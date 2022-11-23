{
    'name': 'Umina Transfers To BZs',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'base',
        'mrp',
        'product',
        'um_mrp_mps'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_product_form_view.xml',
        'views/packing_zone.xml',
        'views/mrp_production_views.xml',
        'views/stock_picking_views.xml',
    ],
    'description': """This module allows custom transfers to every buffer zone associated with workcenter""",
    'license': 'LGPL-3',
}