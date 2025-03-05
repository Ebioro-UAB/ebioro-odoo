from odoo import _, api, models, fields
from odoo.exceptions import ValidationError
import logging
import requests
import json
import time
import hmac
import hashlib
from urllib.parse import urlparse, parse_qs
import math

from werkzeug import urls

_logger = logging.getLogger(__name__)
_logger.info('Payment Transaction Ebioro')

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    ebioro_public_key = fields.Char(related='provider_id.ebioro_public_key', readonly=True)
    ebioro_secret_key = fields.Char(related='provider_id.ebioro_secret_key', readonly=True)

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return Ebioro-specific rendering values.

        Note: self.ensure_one()

        :param dict processing_values: The generic and specific processing values
        :return: The dict of provider-specific processing values
        :rtype: dict
        """

        _logger.debug("Entering Ebioro _get_specific_rendering_values")
        res = super()._get_specific_rendering_values(processing_values)
        _logger.debug("Provider code: %s", self.provider_code)
        if self.provider_code != 'ebioro':
            return res

        response = self._send_payment_request()
        if response and 'url' in response:

            rendering_values = {
                'return_url': response['url'],
                'lang': response['lang'][0],
                'paymentId': response['paymentId'][0],
                'auth_token': response['auth_token'][0],
            }
        
            _logger.info('Ebioro: Payment request successful for transaction %s', rendering_values)
            return rendering_values
        else:
            raise ValidationError(_("No redirect URL received from Ebioro"))

    def _get_return_url(self):
        """ Helper method to get the return URL """
        return self.get_base_url() + '/payments/ebioro/return'

    def _get_webhook_url(self):
        """ Helper method to get the webhook URL """
        return self.get_base_url() + '/payments/ebioro/webhook'

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != 'ebioro':
            return

        # Process the notification data from Ebioro
        status = notification_data.get('status')
        if status == 'completed':
            self._set_done()
            _logger.info('Ebioro: Payment successful for transaction %s', self.reference)
        elif status == 'pending':
            self._set_pending()
            _logger.info('Ebioro: Payment pending for transaction %s', self.reference)
        elif status == 'authorized':
            self._set_authorized()
            _logger.info('Ebioro: Payment authorized for transaction %s', self.reference)
        elif status == 'failed':
            error_msg = notification_data.get('error', 'Unknown error')
            _logger.error('Ebioro: Payment failed for transaction %s. Error: %s', 
                         self.reference, error_msg)
            self._set_error(f"Payment failed: {error_msg}")
        elif status == 'cancelled':
            _logger.info('Ebioro: Payment cancelled for transaction %s', self.reference)
            self._set_canceled()
        else:
            _logger.error('Ebioro: Received unrecognized payment status: %s', status)
            self._set_error("Received unknown payment status")

    def _send_payment_request(self):
        _logger.info('ENTER SEND PAYMENT REQUEST')
        """ Override of payment to handle the payment request to Ebioro.

        Note: self.ensure_one()

        :return: None
        :raise: ValidationError if the transaction cannot be processed
        """
        super()._send_payment_request()
        if self.provider_code != 'ebioro':
            return

        # Make the payment request to Ebioro
        payload = {
            "amount": {
                "currency": self.currency_id.name,
                "value": math.trunc(self.amount * 100)
            },
            "description": "Payment for order",
            "redirectUrl": 'http://127.0.0.1:8069/payments/ebioro/return',
            "name": self.partner_name,
            "cancelUrl": 'http://127.0.0.1:8069/payments/ebioro/return',
            "webhookUrl": 'http://127.0.0.1:8069/payments/ebioro/webhook',
            "locale": "en",
            "metadata": {
                "orderId": self.reference
            }
        }

        status = self.provider_id.state

        _logger.info('PROVIDER STATUS')
        _logger.info(status)

        base_url = 'https://test-merchant.ebioro.com' if status == 'test' else 'https://test-merchant.ebioro.com'
        endpoint = '/payments'

        headers = self._generate_headers(method="POST", path=endpoint, body=payload)

        url = f"{base_url}{endpoint}"
        print("\n=== Request Details ===")
        print(f"URL: {url}")
        print("\nHeaders:")
        print(json.dumps(headers, indent=2))
        print("\nPayload:")
        print(json.dumps(payload, indent=2))

        try:
            # TODO: Replace with actual Ebioro API endpoint

            response = requests.post(url, headers=headers, json=payload)
            print("\n=== Response Details ===")
            print(f"Status Code: {response.status_code}")
            print("\nResponse Body:")

            try:
                print(json.dumps(response.json(), indent=2))
                response.raise_for_status()
                response_data = response.json()

                _logger.info('Ebioro: Payment request successful for transaction %s', response_data)

                redirect_url = response_data.get('hostedUrl')

                extracted_params = self._extract_params(redirect_url)
                redirect_url = extracted_params['base_url']# + '?' + extracted_params['query_params']

                if redirect_url:
                    return {
                        'type': 'ir.actions.act_url',
                        'url': redirect_url,
                        'lang': extracted_params['query_params']['lang'],
                        'paymentId': extracted_params['query_params']['paymentId'],
                        'auth_token': extracted_params['query_params']['auth_token'],
                        'target': 'self',
                    }
                else:
                    raise ValidationError(_("No redirect URL received from Ebioro"))
            
            except json.JSONDecodeError:
                print("Non-JSON response:", response.text)
                
        except requests.exceptions.RequestException as e:
            _logger.exception("Could not reach Ebioro")
            print("\nError:", str(e))
            raise ValidationError(_("Could not connect to Ebioro: %s", str(e)))

    
    def _generate_headers(self, method: str, path: str, body: dict = None) -> dict:

        public_key = self.provider_id.ebioro_public_key
        secret_key = self.provider_id.ebioro_secret_key

        data = json.dumps(body, separators=(',', ':')) if body else ""
        timestamp = str(int(time.time()))  # Unix timestamp
        payload_string = path + timestamp + method + data  # Must match backend signing logic

        # Generate HMAC signature
        signature = hmac.new(secret_key.encode('utf-8'), 
                        payload_string.encode('utf-8'), 
                        hashlib.sha256).hexdigest()

        headers = {
            'Content-Type': 'application/json',
            'X-Digest-Key': public_key,
            'X-Digest-Signature': signature,
            'X-Digest-Timestamp': timestamp
        }

        return headers
    
    def _extract_params(self, url):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        return {
            'base_url': base_url,
            'query_params': query_params
        }
