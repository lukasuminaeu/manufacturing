{
    'name': 'Export Products with Images in Excel',
    'author': "Edge Technologies",
    'version': '15.0.1.2',
    'live_test_url': 'https://youtu.be/nZzGsi6Os1Y',
    "images": ["static/description/main_screenshot.png"],
    'summary': 'Export Products images in excel export product in excel export images in excel product image export Products images in xls export product in xls export images in xls product image export product data in excel product export with image export product images',
    'description': """
		Export Products Details with Images
	""",
    "license": "OPL-1",
    'depends': ['sale_management'],
    'data': [
        'security/export_security.xml',
        'security/ir.model.access.csv',
        'wizard/export_product_view.xml',

        'view/product_categery_parts_view.xml'
    ],
    'qweb': [],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'price': 12.0,
    'currency': "EUR",
    'category': 'Customizations',

    # Enable this to app to be displayed
    'application': True,
    #'sequence': -1,
}
