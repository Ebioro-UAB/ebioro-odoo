try:
    from odoo.tools import LazyTranslate
except ImportError:
    from odoo.tools.translate import _ as LazyTranslate

_lt = LazyTranslate(__name__) if hasattr(LazyTranslate, '__call__') else LazyTranslate


# Ebioro merchant API base URLs, keyed by the provider's `state` field.
# 'enabled' = production, 'test' = sandbox. Hosts match the WooCommerce plugin.
API_URLS = {
    'enabled': 'https://merchant-api.ebioro.com',
    'test': 'https://test-merchant.ebioro.com',
}

# Currencies supported by Ebioro (ISO 4217). The platform settles in USDC.
SUPPORTED_CURRENCIES = [
    'USD',
]

# The codes of the payment methods to activate when Ebioro is activated.
DEFAULT_PAYMENT_METHOD_CODES = {
    'ebioro_wallet',
}

# Mapping of Odoo transaction states to Ebioro payment statuses.
# Tuples only — a bare string here would make `status in (...)` do substring
# matching (e.g. 'paid' in 'unpaid').
TRANSACTION_STATUS_MAPPING = {
    'pending': ('open', 'processing', 'underpaid'),
    'done': ('paid',),
    'canceled': ('canceled', 'expired', 'refunded'),
    'error': ('failed',),
}

EBIORO_TRANSACTION_STATES = [
    'transaction_created',
    'transaction_updated',
    'transaction_failed',
]

EBIORO_SETTLEMENT_STATES = [
    'open',
    'paid',
    'processing',
]
