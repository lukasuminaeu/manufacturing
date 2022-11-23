# -*- coding: utf-8 -*-
{
    'name': "um_lots",

    'summary': """
        Module for Ecowood project, mostly related to transfers modifications.""",

    'description': """
        Moving products from one location to other with additional functionality.
        Automatically creates new transfers depending on what transfer been made.
        Lots now have some more additional fields that are being processed on transfers.
    """,

    'author': "Umina",
    'website': "https://umina.odoo.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Customizations',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'sale',
        'stock',
        'product'
    ],
    'license': 'LGPL-3',

    # always loaded
    'data': [

        # start up data config data
        'data/settings_stock.xml',
        'data/inventory_locations.xml',
        'data/warehouse.xml',
        'data/inventory_operation_types.xml',
        'data/products.xml',
        'data/product_data.xml',
        'data/uom_data.xml',

        # 'security/ir.model.access.csv',
        'views/stock_production_lot_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_quant_views.xml',
        'views/stock_move_line_views.xml',
    ],
}
