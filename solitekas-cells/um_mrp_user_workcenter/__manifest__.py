# -*- encoding: utf-8 -*-

{
    'name': 'Umina User Workcenter',
    'version': '1.0',
    'category': 'Stock',
    'sequence': 50,
    'summary': 'Umina User Workcenter',
    'depends': [
        'mrp_workorder', 'web', 'um_mrp_mps',
    ],
    'description': """

""",
    'data': [
        'views/res_user_views.xml',
        'views/mrp_views.xml',
        'views/mrp_views_menus.xml',
        'views/mrp_production_views.xml',
    ],
    'demo': [
    ],
    'assets': {
        'web.assets_backend': [
            'um_mrp_user_workcenter/static/js/kanban_view.js',
        ],
    },
    'application': False,
    'license': 'LGPL-3',
}
