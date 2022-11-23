# -*- coding: utf-8 -*-
{
    'name': "Umina MRP Config",

    'summary': """Umina MRP Config""",

    'author': "Umina",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Manufacturing/Manufacturing',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': [
        'quality_mrp',
        'sale_stock',
        'base', 
        'stock',
        # 'product_matrix',
        'mrp', 
        'web_studio', 
        'sale',
        'uom',
        # 'sale_product_matrix',
        # 'purchase_product_matrix',
        'um_mrp_mps', 
        'um_mrp_repairs', 
        'um_mrp_workorder', 
        'um_scrap_all_cells', 
        'um_stock_receipt',
        'um_mrp_select_variations',
        'um_mrp_user_workcenter',
        'um_transfers_bz',
        'hide_menu_user',
        ],
    # always loaded
    'data': [
        'data/settings_configuration.xml',
        'data/activate_routes.xml',
        'data/inventory_locations.xml',
        'data/product_product.xml',
        'data/bom_components.xml', # Do not use this file when testing data is not used anymore!
        'data/bill_of_materials_w_components.xml', # Do not use this file when testing data is not used anymore!
        # 'data/bill_of_materials.xml', # Use this file when testing data is not used anymore!
        'data/mrp_workcenter.xml',
        'data/mrp_routing_workcenter.xml',
        'data/warehouse.xml',
        # 'data/inventory_routes.xml',
        'data/inventory_operation_types.xml',
        'data/inventory_configuration_rules.xml',
        'data/inventory_automated_action.xml',
        'views/mrp_production_views.xml',
        'data/res_users.xml',
        'data/quality_point.xml',
        'data/uom_data.xml',
    ],
    'application': False,
    'license': 'LGPL-3',
}
