# -*- coding: utf-8 -*-
{
    'name': "ecowood_sorting",

    'summary': """
        ecowood sorting module.""",

    'description': """
        Individually process items using barcode scanner.
    """,

    'author': "Umina",
    'website': "https://umina.odoo.com",

    'category': 'Customizations',
    'version': '0.0.6',

    # any module necessary for this one to work correctly
    'depends': ['base',  'um_lots', 'stock',  'timer'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',

        # Views
        'views/sorting_tree_view.xml',
        'views/sorting_form_view.xml',
        'views/stock_picking_views.xml',
        'views/sorting_saved_operation_view.xml',
        'views/rusys_receit_view.xml',
        'views/sorting_popup_view.xml',

        # Wizard
        'wizard/sorting_wizard_view.xml',
        'wizard/bought_wizard_view.xml',

        # Data
        'data/inventory_locations.xml',
        'data/inventory_operation_types.xml',
        'data/products.xml',

        # Confirm wizard
        'confirm_wizard/confirm_wizard.xml',

        # Debug
        'debug/debug_menu_view.xml',

            # Debug barcode entry
        'debug/debug_barcode_wizard.xml',

    ],
    'license': 'LGPL-3',

}
