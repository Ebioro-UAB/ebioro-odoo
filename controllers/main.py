from odoo import http
from odoo.http import request
import hmac
import hashlib
import logging

_logger = logging.getLogger(__name__)


class EbioroController(http.Controller):

    @http.route('/payments/ebioro/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def ebioro_webhook(self, **post):
        """ Handle the signed webhook notifications from Ebioro.

        The HMAC signature over the raw body is the only thing we trust to
        change a transaction's state — the customer-facing return route does
        not (see ``ebioro_return``).
        """
        signature = request.httprequest.headers.get('X-Webhook-Auth')
        if not signature:
            _logger.warning("Ebioro webhook rejected: missing signature")
            return http.Response("Bad request", status=400)

        raw_body = request.httprequest.get_data()
        try:
            payload = request.get_json_data().get('data', {})
        except Exception:
            _logger.warning("Ebioro webhook rejected: body is not valid JSON")
            return http.Response("Bad request", status=400)

        tx_reference = payload.get('metadata', {}).get('orderId')
        if not tx_reference:
            _logger.warning("Ebioro webhook rejected: no order reference")
            return http.Response("Bad request", status=400)

        tx = request.env['payment.transaction'].sudo().search(
            [('reference', '=', tx_reference), ('provider_code', '=', 'ebioro')], limit=1
        )

        # Uniform 400 whether the reference is unknown or the signature is wrong,
        # so the endpoint can't be used to probe which order references exist.
        if not tx or not tx.provider_id.ebioro_secret_key:
            _logger.warning("Ebioro webhook rejected for reference %s", tx_reference)
            return http.Response("Bad request", status=400)

        expected_signature = hmac.new(
            tx.provider_id.ebioro_secret_key.encode('utf-8'),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            _logger.warning("Ebioro webhook rejected: invalid signature for %s", tx_reference)
            return http.Response("Bad request", status=400)

        _logger.info("Processing verified Ebioro webhook for transaction %s", tx_reference)
        request.env['payment.transaction'].sudo()._handle_notification_data('ebioro', payload)
        return http.Response("OK", status=200)

    @http.route('/payments/ebioro/return', type='http', auth='public', csrf=False)
    def ebioro_return(self, **data):
        """ Handle the customer's return from the Ebioro payment page.

        This route is reached by the customer's browser with query parameters
        that are NOT authenticated, so it must never change a transaction's
        state — doing so would let anyone mark an order paid by crafting a URL.
        The real status arrives via the signed webhook. Here we only send the
        customer to the standard payment status page, which polls the (already
        webhook-updated) transaction.
        """
        # Don't log the full query string at INFO — it carries auth_token / paymentId.
        _logger.info("Customer returned from Ebioro payment page (payment %s)", data.get('paymentId', 'unknown'))
        return request.redirect('/payment/status')
