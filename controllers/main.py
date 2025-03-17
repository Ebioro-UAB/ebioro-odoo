from odoo import http
from odoo.http import request
import hmac
import hashlib
import logging
import json
import pprint
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class EbioroController(http.Controller):
    
    @http.route('/payments/ebioro/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def ebioro_webhook(self, **post):
        """ Handle the webhook notifications from Ebioro """

        _logger.info("Ebioro Webhook Headers: %s", dict(request.httprequest.headers))
        
        # Verify webhook signature
        signature = request.httprequest.headers.get('X-Webhook-Auth')
        if not signature:
            _logger.error("No signature found in Ebioro webhook")
            return 'No signature', 400

        data = request.get_json_data()
        payload = data.get('data', {})
        tx_reference = payload.get('metadata', {}).get('orderId')
        if not tx_reference:
            _logger.error("No transaction reference found in Ebioro webhook")
            return 'No transaction reference', 400

        tx = request.env['payment.transaction'].sudo().search([('reference', '=', tx_reference)])
        if not tx:
            _logger.error("No transaction found for reference %s", tx_reference)
            return 'Transaction not found', 404

        # Verify webhook signature
        payloadHttp = request.httprequest.get_data()
        _logger.info("Payload for transaction %s: %s", tx_reference, payloadHttp)
        expected_signature = hmac.new(
            tx.provider_id.ebioro_secret_key.encode('utf-8'),
            payloadHttp,
            hashlib.sha256
        ).hexdigest()

        _logger.info("Expected signature: %s", expected_signature)

        if not hmac.compare_digest(signature, expected_signature):
            _logger.error("Invalid webhook signature for transaction %s", tx_reference)
            return 'Invalid signature', 400

        # Process the webhook data
        _logger.info("Processing Ebioro webhook data for transaction %s", tx_reference)
        request.env['payment.transaction'].sudo()._handle_notification_data('ebioro', payload)
        return 'OK'

    @http.route('/payments/ebioro/return', type='http', auth='public', csrf=False)
    def ebioro_return(self, **data):
        """ Handle the return from Ebioro payment page """
        _logger.info("Handling return from Ebioro payment page: %s", data)
        
        # Handle the return data
        if not data:
            _logger.error("No data received from Ebioro return")
            return request.redirect('/payment/status')

        tx_reference = data.get('reference')
        if not tx_reference:
            _logger.error("No transaction reference in return data")
            return request.redirect('/payment/status')

        tx = request.env['payment.transaction'].sudo().search([('reference', '=', tx_reference)])
        if not tx:
            _logger.error("No transaction found for reference %s", tx_reference)
            return request.redirect('/payment/status')

        # Process the return data
        request.env['payment.transaction'].sudo()._handle_notification_data('ebioro', data)
        return request.redirect('/payment/status')
