from odoo import fields, models


class PaymentMethod(models.Model):
    _inherit = 'payment.method'

    support_refund = fields.Selection(
        selection_add=[('none', "None")],
        ondelete={'none': 'set default'},
        default='fully_only',
    )
