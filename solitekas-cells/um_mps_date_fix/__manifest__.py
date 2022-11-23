# -*- coding: utf-8 -*-
{
    'name': "um_mps_date_fix",

    'summary': """
        """,

    'description': """
        Date fix when creating MO's from MPS. Now, as we were creating lets say for
        date of 2022-10-03, so in backend it was created at 2022-10-02 23:00:00 for somewhat
        reason so that was making some problems later when calculating values in MPS.
    """,

    'author': "Umina",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mrp'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
    ],
    # only loaded in demonstration mode
}
