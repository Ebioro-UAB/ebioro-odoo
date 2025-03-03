from odoo import http
from odoo.http import request
import hmac
import hashlib
import logging

_logger = logging.getLogger(__name__)

class EbioroController(http.Controller):
    
    @http.route('/payment/ebioro/webhook', type='json', auth='public', csrf=False)
    def ebioro_webhook(self, **post):
        """ Handle the webhook notifications from Ebioro """
        # Verify webhook signature
        signature = request.httprequest.headers.get('X-Ebioro-Signature')
        if not signature:
            _logger.error("No signature found in Ebioro webhook")
            return 'No signature', 400

        tx_reference = post.get('reference')
        if not tx_reference:
            _logger.error("No transaction reference found in Ebioro webhook")
            return 'No transaction reference', 400

        tx = request.env['payment.transaction'].sudo().search([('reference', '=', tx_reference)])
        if not tx:
            _logger.error("No transaction found for reference %s", tx_reference)
            return 'Transaction not found', 404

        # Verify webhook signature
        received_signature = signature.split('=')[-1]
        payload = request.httprequest.get_data()
        expected_signature = hmac.new(
            # tx.provider_id.ebioro_webhook_key.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.error("Invalid webhook signature for transaction %s", tx_reference)
            return 'Invalid signature', 400

        # Process the webhook data
        _logger.info("Processing Ebioro webhook data for transaction %s", tx_reference)
        request.env['payment.transaction'].sudo()._handle_notification_data('ebioro', post)
        return 'OK'

    @http.route('/payment/ebioro/return', type='http', auth='public', csrf=False)
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
