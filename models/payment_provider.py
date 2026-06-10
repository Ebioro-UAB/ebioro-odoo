import logging
from odoo import api, fields, models
from odoo.addons.payment_ebioro import const

_logger = logging.getLogger(__name__)

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('ebioro', "Ebioro")],
        ondelete={'ebioro': 'set default'}
    )

    ebioro_public_key = fields.Char(
        string="Ebioro Public Key",
        help="The API key used to connect with Ebioro payment service.",
        required_if_provider='ebioro'
    )
    ebioro_secret_key = fields.Char(
        string="Ebioro Secret Key",
        help="The secret key used to sign API requests.",
        required_if_provider='ebioro'
    )

    def _compute_feature_support_fields(self):
        """ Override of `payment` to declare Ebioro's supported features.

        Setting support_refund enables the refund button on completed
        transactions, which routes to PaymentTransaction._send_refund_request.
        """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'ebioro').update({
            'support_refund': 'full_only',
        })

    def _get_supported_currencies(self):
        """ Override of `payment` to limit Ebioro to the currencies it settles in. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'ebioro':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'ebioro':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    def _ebioro_get_api_url(self):
        """ Return the Ebioro API base URL for this provider's state. """
        self.ensure_one()
        return const.API_URLS.get(self.state, const.API_URLS['test'])
