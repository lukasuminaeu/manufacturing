# -*- encoding: utf-8 -*-

{
    'name': 'Umina MRP Workorder',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'sequence': 50,
    'summary': 'Umina MRP Workorder Customizations',
    'depends': [
        'mrp_workorder',
        'mrp',
        'bus',
        'stock',
        'um_retry_function_wrapper',
        'um_mrp_repairs',
        'um_mrp_user_workcenter'
    ],
    'description': """

""",
    'data': [
        'views/mrp_workorder_report.xml',
        'views/mrp_workorder_views.xml',
        'views/report_workorder_templates.xml',
        'views/mrp_production_views.xml',
    ],
    'demo': [
    ],
    'assets': {},
    'application': False,
    'license': 'LGPL-3',
}
