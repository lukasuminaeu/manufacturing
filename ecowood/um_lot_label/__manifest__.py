# -*- coding: utf-8 -*-
{
    'name': "um_lot_label",

    'summary': """
        Lot label customization""",

    'description': """
        
    """,

    'author': "Aleksandr Matvejev",
    'website': "https://www.umina.eu/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
        'reports/report_lot_barcode.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
