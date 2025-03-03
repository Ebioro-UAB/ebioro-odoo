from odoo import _, api, models, fields
from odoo.exceptions import ValidationError
import logging
import requests
import json
import time
import hmac
import hashlib

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

        base_url = "https://test-merchant.ebioro.com"

        # Extract the payment link URL and params and embed them in the redirect form.
        # parsed_url = urls.url_parse(base_url)
        # url_params = urls.url_decode(parsed_url.query)
        # rendering_values = {
        #     'api_url': base_url,
        #     'url_params': url_params,  # Encore the params as inputs to preserve them.
        # }

        # return rendering_values

        return {
            'public_key': self.provider_id.ebioro_public_key,
            'amount': self.amount,
            'currency': self.currency_id.name,
            'reference': self.reference,
            'partner_name': self.partner_name,
            'partner_email': self.partner_email,
            'return_url': f"{base_url}/payment/ebioro/return",
            'webhook_url': f"{base_url}/payment/ebioro/webhook",
            'cancel_url': f"{base_url}/payment/status",
            'provider_id': self.provider_id.id
        }

    def action_pay_now(self):
        self.ensure_one()
        if self.provider_code != 'ebioro':
            raise ValidationError(_("This action is only available for Ebioro transactions."))

        # Redirect to external URL
        external_url = "https://test-merchant.ebioro.com/"
        return {
            'type': 'ir.actions.act_url',
            'url': external_url,
            'target': 'new',
        }

    def _get_return_url(self):
        """ Helper method to get the return URL """
        return self.get_base_url() + '/payment/ebioro/return'

    def _get_webhook_url(self):
        """ Helper method to get the webhook URL """
        return self.get_base_url() + '/payment/ebioro/webhook'

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
            'amount': {
                'currency': self.currency_id.name,
                'value': self.amount
            },
            'redirectUrl': self._get_return_url(),
            'cancelUrl': self._get_return_url(),
            'webhookUrl': self._get_webhook_url(),
            'description': "Ebioro payment",
            'name': self.partner_name,
            'metadata': {
                'reference': self.reference
            }
        }

        status = self.provider_id.state

        print('PROVIDER STATUS')
        print(status)

        url = 'https://test-merchant.ebioro.com/' if status == 'test' else 'https://test-merchant.ebioro.com/'

        try:
            # TODO: Replace with actual Ebioro API endpoint
            response = requests.post(
                url,
                headers=self._generate_headers('POST', '/payments', payload),
                data=json.dumps(payload, separators=(',', ':'))
            )
            response.raise_for_status()
            response_data = response.json()
            notification_data = {'reference': self.reference}
            self._handle_notification_data('ebioro', notification_data)
                
        except requests.exceptions.RequestException as e:
            _logger.exception("Could not reach Ebioro")
            raise ValidationError(_("Could not connect to Ebioro: %s", str(e)))

    
    def _generate_headers(self, method: str, path: str, body: dict = None) -> dict:

        public_key = self.provider_id.ebioro_public_key
        secret_key = self.provider_id.ebioro_secret_key

        data = json.dumps(body, separators=(',', ':')) if body else ""
        timestamp = str(int(time.time()))
        signature_data = f"{path}{timestamp}{method}{data}"
        signature = hmac.new(
            secret_key.encode(),
            signature_data.encode(),
            hashlib.sha256
        ).hexdigest()

        return {
            'Content-Type': 'application/json',
            'x-digest-key': public_key,
            'x-digest-timestamp': timestamp,
            'x-digest-signature': signature
        }
