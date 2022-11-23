# -*- coding: utf-8 -*-
{
    'name': "Product Pictures",

    'summary': """Product pictures""",

    'description': """
        Upload multiple product pictures and set it as avatar
    """,

    'author': "Unima",
    'website': "https://www.umina.eu/",

    'category': 'Customizations',
    'version': '0.3.3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/quotations_picture_tab_view.xml',
        'views/product_dimensions_fields_view.xml',

    ],
    # Enable this to app to be displayed
    'application': True,
    #'sequence': -1,
    'license': 'LGPL-3',

}
