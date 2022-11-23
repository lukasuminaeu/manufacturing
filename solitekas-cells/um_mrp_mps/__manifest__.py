# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Umina Master Production Schedule',
    'version': '2.0',
    'category': 'Manufacturing/Manufacturing',
    'sequence': 50,
    'summary': 'Master Production Schedule',
    'depends': [
        'mrp_mps',
        'quality',
        'quality_mrp_workorder',
        'stock_no_negative',
    ],
    'description': """

""",
    'data': [
        'views/mrp_workcenter.xml',
        'views/mrp_production_views.xml',
        'views/mrp_workorder_views.xml',
        'views/quality_point_views.xml',
        'views/stock_location_views.xml',
        'views/stock_quant_views.xml',
        # 'views/res_config_settings_views.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_backend': [
            'um_mrp_mps/static/src/js/client_action.js',
            'um_mrp_mps/static/src/scss/client_action.scss',
        ],
        'web.assets_qweb': [
            'um_mrp_mps/static/src/xml/**/*',
        ],
    },
    'application': False,
    'license': 'LGPL-3',
}
