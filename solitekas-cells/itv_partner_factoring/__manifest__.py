# -*- coding: utf-8 -*-
{
    'name': "Itv Partner Factoring",

    'summary': """itv partner factoring """,

    'description': """
        Faktoringo ir faktoringo pranešimo nustatymas kliento kortelėje ir užsakyme
    """,

    'author': "ITVISION",
    'website': "http://www.itvision.lt",

    'category': 'sales',
    'version': '1.0',

    'depends': [
        'base',
        'sale',
        'contacts',
    ],

    'data': [
        'views/res_partner.xml',
        'views/sale_order.xml',
        # 'security/ir.model.access.csv',
        # # 'views/views.xml',
        # 'views/sms_views.xml',
    ],
}
