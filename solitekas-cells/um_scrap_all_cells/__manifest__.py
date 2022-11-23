# -*- coding: utf-8 -*-
{
    'name': "um_scrap_all",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'stock',
        'mrp',
        'mrp_workorder'
    ],

    # always loaded
    'data': [
        'views/mrp_workorder_views.xml',
        'security/ir.model.access.csv',
        # 'wizards/scrap_all_wizard_views.xml'
    ],
    'license': 'LGPL-3',
}
