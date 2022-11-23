# -*- coding: utf-8 -*-
###############################################################################
#
#    info@itvision.lt
#
#    Copyright (c) All rights reserved:
#        (c) 2019  ITVISION
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses
#
#    Odoo is trademark of Odoo S.A.
#
###############################################################################
{
    'name': "Cells Sale",
    'summary': "Solitek Cells",
    'version': '1.0',

    'description': """
        
    """,
    'author': "ITVISION",
    'maintainer': 'ITVISION',
    'contributors': ['ITVISION <info@itvision.lt>'],

    'website': 'https://www.itvision.lt',

    'license': 'AGPL-3',
    'category': 'Sale',

    'depends': [
        'base',
        'sale',
        'base_automation',
        'sales_team',
        'crm',
        'account',
        'itv_partner_factoring',
        'partner_registry_code',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/cancel_reason_data.xml',
        'data/automation_rule_data.xml',
        'wizard/sale_order_cancel_views.xml',
        'report/sale_report_templates.xml',
        'views/sale_views.xml',
        'views/sale_cancel_reason_views.xml',
        'views/crm_views.xml',
        'views/report_templates.xml',
        # 'data/report_layout.xml',
        'report/sale_report.xml',
        'report/invoice_report.xml',
        'report/account_report.xml',
        'views/account_move_views.xml',
        'report/delivery_slip_report.xml',
        'views/bank_form.xml',
    ],
    'images': [
        # 'static/description/image.jpg',
    ],
    # 'qweb': ['static/src/xml/*.xml'],
    # 'external_dependencies': {
    #     'python': [
    #         'xlrd',
    #         # 'pyodbc'
    #     ],
    # },
    'installable': True
}
