from . import models
from . import controllers

from odoo.addons.payment import setup_provider, reset_payment_provider


def post_init_hook(env):
    setup_provider(env, 'ebioro')
    # Activate the payment method only after the provider is fully set up —
    # activating it from data XML races provider setup during install.
    method = env.ref('payment_ebioro.payment_method_ebioro_wallet')
    method.active = True


def uninstall_hook(env):
    reset_payment_provider(env, 'ebioro')
