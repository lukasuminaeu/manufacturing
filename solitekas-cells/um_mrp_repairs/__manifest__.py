{
    'name': 'Umina Repairs',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'base',
        'mrp_mps',
        'quality_control',
        'repair',
        'product',
        'stock_barcode',
        'um_scrap_all_cells',
        'um_retry_function_wrapper',
    ],
    'data': [
        'views/quality_check_fail.xml',
        'views/repair_order_form_view_remade.xml',
        'views/repair_workorder_tablet_view.xml',
        'views/stock_location_views.xml',
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
}