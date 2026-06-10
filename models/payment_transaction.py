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

from odoo.addons.payment_ebioro import const
from werkzeug import urls

_logger = logging.getLogger(__name__)
_logger.info('Payment Transaction Ebioro')

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    ebioro_public_key = fields.Char(related='provider_id.ebioro_public_key', readonly=True)
    ebioro_secret_key = fields.Char(related='provider_id.ebioro_secret_key', readonly=True)
    ebioro_transaction_id = fields.Char(string="Ebioro Transaction ID", help="Stores the external Ebioro payment transaction ID")

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
        if response and 'return_url' in response:

            rendering_values = {
                'return_url': response['return_url'],
                'lang': response['lang'][0],
                'paymentId': response['paymentId'][0],
                'auth_token': response['auth_token'][0],
            }

            _logger.info('Ebioro: Payment request successful for transaction %s', rendering_values)
            return rendering_values
        else:
            _logger.error('Ebioro: No redirect URL received in _get_specific_rendering_values')
            raise ValidationError(_("No redirect URL received from Ebioro"))

    def _get_return_url(self):
        """ Helper method to get the return URL """
        return self.get_base_url() + '/payments/ebioro/return'

    def _get_webhook_url(self):
        """ Helper method to get the webhook URL """
        return self.get_base_url() + '/payments/ebioro/webhook'

    def _process_notification_data(self, notification_data):

        _logger.info("EBIORO WEBHOOK DATA _process_notification_data: %s", notification_data)


        super()._process_notification_data(notification_data)
        if self.provider_code != 'ebioro':
            return

        # Process the notification data from Ebioro
        status = notification_data.get('status')
        
        if status in const.TRANSACTION_STATUS_MAPPING['pending']:
            self._set_pending()
            _logger.info('Ebioro: Payment pending for transaction %s', self.reference)
        elif status in const.TRANSACTION_STATUS_MAPPING['done']:
            self._set_done()
            _logger.info('Ebioro: Payment done for transaction %s', self.reference)
        elif status in const.TRANSACTION_STATUS_MAPPING['canceled']:
            self._set_canceled()
        elif status in const.TRANSACTION_STATUS_MAPPING['error']:
            error_msg = notification_data.get('error', 'Unknown error')
            _logger.error('Ebioro: Payment failed for transaction %s. Error: %s', 
                        self.reference, error_msg)
            self._set_error(f"Payment failed: {error_msg}")
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
        
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

        # Make the payment request to Ebioro
        payload = {
            "amount": {
                "currency": usd_currency.name,
                "value": math.trunc(self.amount * 100)
            },
            "description": "Payment for order %s" % self.reference,
            "redirectUrl": self._get_return_url(),
            "name": self.env['website'].get_current_website().name,
            "cancelUrl": self._get_return_url(),
            "webhookUrl": self._get_webhook_url(),
            "locale": "en",
            "metadata": {
                "orderId": self.reference
            }
        }

        _logger.info(payload)

        status = self.provider_id.state

        _logger.info('PROVIDER STATUS')
        _logger.info(status)

        base_url = 'https://test-merchant.ebioro.com' if status == 'test' else 'https://test-merchant.ebioro.com'
        endpoint = '/payments'

        headers = self._generate_headers(method="POST", path=endpoint, body=payload)

        url = f"{base_url}{endpoint}"
        _logger.info("\n=== Request Details ===")
        _logger.info(f"URL: {url}")
        _logger.info("\nHeaders:")
        _logger.info(json.dumps(headers, indent=2))
        _logger.info("\nPayload:")
        _logger.info(json.dumps(payload, indent=2))

        try:
            data = json.dumps(payload, separators=(',', ':'))
            response = requests.post(url, headers=headers, data=data)
            _logger.info("\n=== Response Details ===")
            _logger.info(f"Status Code: {response.status_code}")
            _logger.info("\nResponse Body:")

            try:
                print(json.dumps(response.json(), indent=2))
                response.raise_for_status()
                response_data = response.json()

                _logger.info('Ebioro: Payment request successful for transaction %s', response_data)

                redirect_url = response_data.get('hostedUrl')

                if redirect_url:
                    # Keep the full hosted URL (with its query parameters) as the
                    # redirect target — stripping it to the base URL loses the
                    # payment context on the hosted page (July 2025 fix, ported
                    # from the odoo_17 branch).
                    extracted_params = self._extract_params(redirect_url)
                    return {
                        'return_url': redirect_url,
                        'lang': extracted_params['query_params']['lang'],
                        'paymentId': extracted_params['query_params']['paymentId'],
                        'auth_token': extracted_params['query_params']['auth_token'],
                    }
                else:
                    _logger.error('Ebioro: No redirect URL received in _send_payment_request')
                    raise ValidationError(_("No redirect URL received from Ebioro"))
            
            except json.JSONDecodeError:
                print("Non-JSON response:", response.text)
                
        except requests.exceptions.RequestException as e:
            _logger.exception("Could not reach Ebioro")
            print("\nError:", str(e))
            raise ValidationError(_("Could not connect to Ebioro: %s", str(e)))

    def _send_refund_request(self, amount_to_refund=None, **kwargs):
        """
        Override of payment to send a refund request to Ebioro.
        :param float amount_to_refund: The amount to refund (in Odoo currency units)
        :return: The refund transaction if any
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund, **kwargs)
        if self.provider_code != 'ebioro':
            return refund_tx
        payment_id = self.ebioro_transaction_id or self.reference
        endpoint = f"/payments/{payment_id}/refunds"
        base_url = 'https://test-merchant.ebioro.com' if self.provider_id.state == 'test' else 'https://merchant.ebioro.com'
        url = f"{base_url}{endpoint}"
        asset_id = self.currency_id.name
        if hasattr(self.currency_id, 'ebioro_asset_id') and self.currency_id.ebioro_asset_id:
            asset_id = self.currency_id.ebioro_asset_id
        value = int(amount_to_refund * 100) if amount_to_refund else int(self.amount * 100)
        payload = {
            "amount": {
                "asset_id": asset_id,
                "value": value
            },
            "description": f"Refund for order {self.reference}",
            "metadata": {
                "orderId": self.reference
            }
        }
        headers = self._generate_headers(method="POST", path=endpoint, body=payload)
        data = json.dumps(payload, separators=(',', ':'))
        _logger.info("Sending Ebioro refund request: %s", url)
        _logger.info("Payload: %s", data)
        _logger.info("Headers: %s", headers)
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            response_data = response.json()
            _logger.info("Ebioro refund response: %s", response_data)
            refund_tx.ebioro_refund_id = response_data.get('id')
        except Exception as e:
            _logger.error("Ebioro refund failed: %s", str(e))
            raise ValidationError(_("Ebioro refund failed: %s", str(e)))
        return refund_tx

    def _generate_headers(self, method: str, path: str, body: dict = None) -> dict:

        public_key = self.provider_id.ebioro_public_key
        secret_key = self.provider_id.ebioro_secret_key

        payload_string, timestamp = self._generate_payload_string(method, path, body)

        # Generate HMAC signature
        signature = self._generate_signature(payload_string, secret_key)

        headers = {
            'Content-Type': 'application/json',
            'X-Digest-Key': public_key,
            'X-Digest-Signature': signature,
            'X-Digest-Timestamp': timestamp
        }

        return headers
    
    def _generate_payload_string(self, method: str, path: str, body: dict = None):
        data = json.dumps(body, separators=(',', ':')) if body else ""
        timestamp = str(int(time.time()))  # Unix timestamp
        payload_string = path + timestamp + method + data  # Must match backend signing logic

        return payload_string, timestamp

    def _generate_signature(self, data, secret_key):
        return hmac.new(secret_key.encode('utf-8'), 
                        data.encode('utf-8'), 
                        hashlib.sha256).hexdigest()
    
    def _extract_params(self, url):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"

        return {
            'base_url': base_url,
            'query_params': query_params
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on APS data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data are received.
        :raise ValidationError: If the data match no transaction.
        """
        _logger.info("EBIORO WEBHOOK DATA _get_tx_from_notification_data: %s", notification_data)
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'ebioro' or len(tx) == 1:
            return tx

        reference = notification_data.get('metadata').get('orderId')
        if not reference:
            raise ValidationError(
                "EBIORO: " + _("Received data with missing reference %(ref)s.", ref=reference)
            )

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'ebioro')])
        if not tx:
            raise ValidationError(
                "EBIORO: " + _("No transaction found matching reference %s.", reference)
            )

        _logger.info("EBIORO: Transaction found for reference %s", reference)
        return tx