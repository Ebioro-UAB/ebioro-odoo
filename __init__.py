from . import models
from . import controllers

from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(env):
    # Links the Ebioro payment method to the provider. Odoo 18 activates the
    # method automatically when the provider is enabled — we must NOT force
    # `method.active = True` here: payment.method.write() rejects activating a
    # method that has no enabled provider yet, which aborts the install.
    setup_provider(env, 'ebioro')


def uninstall_hook(env):
    reset_payment_provider(env, 'ebioro')
