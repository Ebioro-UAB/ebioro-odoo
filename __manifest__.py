{
    'name': 'Ebioro Payment Provider',
    'version': '18.0.1.1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': 'Payment Provider: Ebioro Implementation',
    'description': """Ebioro Payment Provider""",
    'author': 'Ebioro UAB',
    'website': 'https://www.ebioro.com',
    'depends': ['payment'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_provider_redirect_form.xml',
        'data/payment_method_data.xml',
        'data/payment_provider_data.xml',
        'views/payment_provider_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'LGPL-3'
}
