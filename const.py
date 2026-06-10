try:
    from odoo.tools import LazyTranslate
except ImportError:
    from odoo.tools.translate import _ as LazyTranslate

_lt = LazyTranslate(__name__) if hasattr(LazyTranslate, '__call__') else LazyTranslate


# Currency codes of the currencies supported by Mercado Pago in ISO 4217 format.
# See https://api.mercadopago.com/currencies. Last seen online: 2024-10-29.
SUPPORTED_CURRENCIES = [
    'USD',  # US Dollars
]

# Set of currencies where Mercado Pago's minor units deviates from the ISO 4217 standard.
# See https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xls
# vs. https://api.mercadopago.com/currencies. Last seen online: 2024-10-29.
CURRENCY_DECIMALS = {
    'COP': 0,
    'HNL': 0,
    'NIO': 0,
}

# The codes of the payment methods to activate when Mercado Pago is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    # Primary payment methods.
    'ebioro_wallet'
}

# Mapping of payment method codes to Mercado Pago codes.
PAYMENT_METHODS_MAPPING = {
    'card': 'debit_card,credit_card,prepaid_card'
}

# Mapping of transaction states to Mercado Pago payment statuses.
# See https://www.mercadopago.com.mx/developers/en/reference/payments/_payments_id/get.
TRANSACTION_STATUS_MAPPING = {
    'pending': ('open', 'processing'),
    'done': ('paid'),
    'canceled': ('canceled', 'expired', 'refunded'),
    'error': ('failed',),
}

EBIORO_TRANSACTION_STATES = [
    'transaction_created',
    'transaction_updated',
    'transaction_failed'
]

EBIORO_SETTLEMENT_STATES = [
    'open',
    'paid',
    'processing'
]
