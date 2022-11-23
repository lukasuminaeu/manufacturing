{
    'name': 'Umina Select Variations',
    'version': '1.0',
    'category': 'Manufacturing/Manufacturing',
    'depends': [
        'base',
        'mrp',
        'um_mrp_mps'
    ],
    'data': [
        'views/product_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
}