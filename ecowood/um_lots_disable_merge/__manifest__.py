# -*- coding: utf-8 -*-
{
    'name': "um_disable_items_merge",

    'summary': """
           Disable merging items with different lot's""",

    'description': """
        Disable merging items with different lot's
        it there is 2 items with different lots for example:
        1 item: lot:222 quantity: 100
        2 item: lot-222 quantity: 200
        final item count is 300 after clicking mark as todo
    """,

    'author': "Umina",
    'website': "https://umina.odoo.com/",

    'category': 'Customizations',
    'version': '0.2',

    'depends': [
        'base',
        'sale',
        'stock',
        'product'
    ],
    'license': 'LGPL-3',

}
