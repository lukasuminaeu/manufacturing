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
    'name': "Cells Stock Report View",
    'summary': "Cells Stock Report View",
    'version': '13.0.1.0',

    'description': """
        Product demand from work orders
    """,
    'author': "ITVISION",
    'maintainer': 'ITVISION',
    'contributors': ['ITVISION <info@itvision.lt>'],

    'website': 'https://www.itvision.lt',

    'license': 'AGPL-3',
    'category': 'Stock',

    'depends': [
        'base',
        'base_setup',
        'stock',
        'mrp',
    ],
    'data': [
        'security/ir.model.access.csv',
        
        'views/stock_report_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/mrp_production_views.xml',
        # 'views/mrp_bom_views.xml',
    ],
    'images': [
        'static/description/image.jpg',
    ],
    'assets': {
        'web.assets_backend': [
            "/cells_stock_report_view/static/src/js/stock_report_view.js",
            "/cells_stock_report_view/static/src/css/style.css"
        ]
    },

    'qweb': ['static/src/xml/*.xml'],
    'external_dependencies': {
        'python': [
            'xlrd',
            # 'pyodbc'
        ],
    },
    'installable': True
}