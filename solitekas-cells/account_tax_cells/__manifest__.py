# -*- coding: utf-8 -*-
###############################################################################
#
#    ITVISION<info@itvision.lt>
#
#    Copyright (c) All rights reserved:
#        (c) 2017  TM_FULLNAME
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
#    Odoo and OpenERP is trademark of Odoo S.A.
#
###############################################################################
{
    'name': 'Account Tax Cells extended',
    'summary': 'Tax dependand text on invoice',
    'version': '1.0',
    'description': """
    Tax dependand text on invoice
==============================================


    """,
    'author': 'ITVISION',
    'maintainer': 'ITVISION',
    'contributors': ['ITVISION <info@itvision.lt>'],
    'website': 'https://www.gitlab.com/TM_FULLNAME',
    'license': 'AGPL-3',
    'category': 'Uncategorized',
    'depends': ['base', 'account'],
    'external_dependencies': {
        'python': [],
    },
    'data': [
        'views/account_tax.xml',
        'report/report_invoice.xml',
        'data/account_tax.xml',
    ],
    'demo': [],
    'js': [],
    'css': [],
    'qweb': [],
    'images': [],
    'test': [],
    'installable': True
}
