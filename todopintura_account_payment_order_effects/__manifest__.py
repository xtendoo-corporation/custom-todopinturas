# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    'name': 'Todopintura Account Payment Order Effects',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': (
        'Descuento de efectos (giro/SEPA) en órdenes de cobro: anticipo del '
        'banco al subir la remesa y liquidación automática al vencimiento'
    ),
    'author': 'Xtendoo',
    'website': 'https://www.xtendoo.es',
    'license': 'AGPL-3',
    'depends': [
        'account_payment_order',
    ],
    'data': [
        'views/account_payment_mode_views.xml',
        'views/account_payment_views.xml',
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
