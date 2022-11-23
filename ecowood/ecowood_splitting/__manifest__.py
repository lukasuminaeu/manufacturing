# -*- coding: utf-8 -*-
{
    'name': "ecowood_splitting",

    'summary': """
        Ecowood splitting module""",

    'description': """
        Enables user to process items through splitting stage
    """,

    'author': "Ecowood",
    'website': "https://ecowood.eu/",

    'category': 'Customizations',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'um_lots', 'stock', 'ecowood_sorting'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        #data
        'data/inventory_locations.xml',
        'data/inventory_operation_types.xml',

        #views
        'views/splitting_tree_view.xml',
        'views/stock_picking_views.xml',
        'views/splitting_popup_view.xml',

    ],
    'license': 'LGPL-3',
}