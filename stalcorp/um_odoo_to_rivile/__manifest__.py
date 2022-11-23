# -*- coding: utf-8 -*-
{
    'name': "Odoo to Rivile",

    'summary': """ Odoo to Rivile functionality""",

    'author': "Simonas",
    'website': "https://www.umina.eu/",

    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'contacts', 'crm', 'sale', 'stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/view.xml',
    ],
}
