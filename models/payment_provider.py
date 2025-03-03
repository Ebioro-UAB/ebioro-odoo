import logging
from odoo import api, fields, models
from odoo.addons.payment_ebioro import const

_logger = logging.getLogger(__name__)
_logger.info('Payment Provider Ebioro')

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('ebioro', "Ebioro")],
        ondelete={'ebioro': 'set default'}
    )
    supported_methods = fields.Selection([
        ('card', 'Credit Card'),
        ('bank', 'Bank Transfer')
    ], string="Supported Payment Methods", default='card')

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

    def _compute_feature_supports(self):
        super()._compute_feature_supports()
        for provider in self:
            if provider.code == 'ebioro':
                provider.supports_redirect = True

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'ebioro':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
