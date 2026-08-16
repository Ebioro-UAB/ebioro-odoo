from odoo import _, api, models, fields
from odoo.exceptions import ValidationError
import logging
import requests
import json
import time
import hmac
import hashlib

from odoo.addons.payment_ebioro import const
from werkzeug import urls

_logger = logging.getLogger(__name__)

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # Note: the API keys are NOT mirrored onto the transaction. They live only on
    # payment.provider (secret restricted to admins) and are read via sudo where
    # the payment flow needs them — a related field here would re-expose the
    # secret on every transaction record the customer can read.
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
        if response and response.get('return_url'):
            _logger.debug('Ebioro: rendering values ready for transaction %s', self.reference)
            # Only the tokenless short link is handed to the browser.
            return {'return_url': response['return_url']}
        else:
            _logger.error('Ebioro: No redirect URL received in _get_specific_rendering_values')
            raise ValidationError(_("No redirect URL received from Ebioro"))

    def _get_return_url(self):
        """ Helper method to get the return URL """
        return self.get_base_url() + '/payments/ebioro/return'

    def _get_webhook_url(self):
        """ Helper method to get the webhook URL """
        return self.get_base_url() + '/payments/ebioro/webhook'

    def _ebioro_get_merchant_name(self):
        """ Name shown on the Ebioro payment page.

        Falls back gracefully when there is no website in context (e.g. a
        back-office or subscription payment), which `website.get_current_website()`
        would otherwise crash on.
        """
        if 'website' in self.env:
            website = self.env['website'].get_current_website(fallback=True)
            if website:
                return website.name
        return self.company_id.name or 'Ebioro'

    def _process_notification_data(self, notification_data):

        _logger.debug("Ebioro webhook for %s: status=%s", self.reference, notification_data.get('status'))


        super()._process_notification_data(notification_data)
        if self.provider_code != 'ebioro':
            return

        # Defence in depth: reject an event for a different Ebioro payment than the one
        # this transaction was started with (a superseded/retried payment, or a spoofed
        # id). The per-provider HMAC already blocks cross-merchant forgery; this stops a
        # stale/mismatched event from driving the wrong transaction.
        event_pid = notification_data.get('id')
        if event_pid and self.ebioro_transaction_id and event_pid != self.ebioro_transaction_id:
            _logger.warning(
                'Ebioro: webhook payment %s does not match bound %s for tx %s — ignored',
                event_pid, self.ebioro_transaction_id, self.reference,
            )
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
        """ Override of payment to handle the payment request to Ebioro.

        Note: self.ensure_one()

        :return: None
        :raise: ValidationError if the transaction cannot be processed
        """
        super()._send_payment_request()
        if self.provider_code != 'ebioro':
            return
        
        # Amount in minor units. The outer round() is required: 19.99 is
        # 19.9899999…9 in IEEE-754, so int(19.99 * 100) truncates to 1998.
        value = int(round(self.currency_id.round(self.amount) * 100))

        # Make the payment request to Ebioro
        payload = {
            "amount": {
                "currency": self.currency_id.name,
                "value": value
            },
            "description": "Payment for order %s" % self.reference,
            "redirectUrl": self._get_return_url(),
            "name": self._ebioro_get_merchant_name(),
            "cancelUrl": self._get_return_url(),
            "webhookUrl": self._get_webhook_url(),
            "locale": "en",
            "metadata": {
                "orderId": self.reference
            }
        }

        endpoint = '/payments'
        base_url = self.provider_id._ebioro_get_api_url()

        headers = self._generate_headers(method="POST", path=endpoint, body=payload)
        # Scope the payment to this transaction so a retry/double-submit replays
        # the original instead of creating a duplicate. The header is not part of
        # the signed payload, so it is added after the auth headers.
        headers['Idempotency-Key'] = "odoo-%s" % self.reference

        url = f"{base_url}{endpoint}"
        # Debug only — never log the API key or HMAC signature. Redact the auth
        # headers so credentials can't leak into a log drain even at DEBUG level.
        safe_headers = {
            k: ('***' if k in ('X-Digest-Key', 'X-Digest-Signature') else v)
            for k, v in headers.items()
        }
        _logger.debug("Ebioro payment request to %s", url)
        _logger.debug("Headers: %s", json.dumps(safe_headers))
        _logger.debug("Payload: %s", json.dumps(payload))

        try:
            data = json.dumps(payload, separators=(',', ':'))
            response = requests.post(url, headers=headers, data=data)
            _logger.debug("Ebioro response status %s", response.status_code)

            try:
                response.raise_for_status()
                response_data = response.json()

                _logger.debug('Ebioro: payment request successful for transaction %s', self.reference)

                # Bind the Ebioro payment id to this transaction so the webhook can reject
                # an event carrying a different payment id (defence in depth).
                if response_data.get('id'):
                    self.ebioro_transaction_id = response_data['id']

                # Prefer the tokenless short link (no auth_token in the URL); fall back to
                # the hosted URL only if short links are not enabled for the environment.
                redirect_url = response_data.get('shortUrl') or response_data.get('hostedUrl')

                if redirect_url:
                    return {'return_url': redirect_url}
                else:
                    _logger.error('Ebioro: No redirect URL received in _send_payment_request')
                    raise ValidationError(_("No redirect URL received from Ebioro"))
            
            except json.JSONDecodeError:
                _logger.error("Ebioro: non-JSON response for transaction %s", self.reference)
                raise ValidationError(_("Unexpected response from Ebioro"))

        except requests.exceptions.RequestException as e:
            _logger.exception("Could not reach Ebioro")
            raise ValidationError(_("Could not connect to Ebioro: %s", str(e)))

    # NOTE: Refunds are intentionally NOT implemented here.
    #
    # Ebioro payments are non-custodial: settled funds land directly on the
    # merchant's own account, not in an Ebioro-controlled wallet. A refund
    # therefore moves the merchant's own funds and must be signed by the
    # merchant — the refund API returns an unsigned transaction (XDR) that the
    # merchant signs with their Ebioro signing session and submits back.
    #
    # An API-key integration like this Odoo module has no signing session, so
    # it cannot complete a refund. Merchants issue refunds from the Ebioro
    # enterprise portal (Comercio → the payment → Refund), where the signing
    # session is available. Accordingly the payment method keeps
    # support_refund = none, so Odoo shows no refund button for Ebioro.

    def _generate_headers(self, method: str, path: str, body: dict = None) -> dict:

        # _send_payment_request runs in the customer's context at checkout; the
        # secret is admin-restricted, so read the credentials via sudo.
        provider = self.provider_id.sudo()
        public_key = provider.ebioro_public_key
        secret_key = provider.ebioro_secret_key

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

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on APS data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data are received.
        :raise ValidationError: If the data match no transaction.
        """
        _logger.debug("Ebioro _get_tx_from_notification_data for ref %s", notification_data.get('metadata', {}).get('orderId'))
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'ebioro' or len(tx) == 1:
            return tx

        reference = notification_data.get('metadata', {}).get('orderId')
        if not reference:
            raise ValidationError(
                "EBIORO: " + _("Received data with missing reference %(ref)s.", ref=reference)
            )

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'ebioro')])
        if not tx:
            raise ValidationError(
                "EBIORO: " + _("No transaction found matching reference %s.", reference)
            )

        _logger.debug("Ebioro: transaction found for reference %s", reference)
        return tx