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
    'name': "Cells CRM",
    'summary': " ",
    'version': '1.0',

    'description': """
        
    """,
    'author': "ITVISION",
    'maintainer': 'ITVISION',
    'contributors': ['ITVISION <info@itvision.lt>'],

    'website': 'https://www.itvision.lt',

    'license': 'AGPL-3',
    'category': 'CRM',

    'depends': [
        'base',
        'crm',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/itv_crm_lead_view.xml',
    ],
    'images': [
        # 'static/description/image.jpg',
    ],
    'installable': True
}
