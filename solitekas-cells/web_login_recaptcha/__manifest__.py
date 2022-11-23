# -*- coding: utf-8 -*-
{
    'name': "Web Login Recaptcha",
    'summary': """
        Login using Google Recaptcha v3""",
    'description': """
Protect login page with Google Recaptcha
============================================
1. Register recaptcha key https://www.google.com/recaptcha/admin/create
2. Go to Settings -> General Settings -> Integrations. Check "Login Recaptcha" and input your key.
3. Make sure that recaptcha logo appear on login page.
    """,
    'author': "Cak Juice",
    'website': "https://cakjuice.com",
    'category': 'Uncategorized',
    'version': '13.0.1',
    'images': [
        'static/description/main_screenshot.png',
        'static/description/ss_recaptcha_1.png',
        'static/description/ss_recaptcha_2.png',
    ],
    'depends': ['base_setup'],
    'data': [
        'templates/login_template.xml',
        'views/res_config_settings_views.xml',
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}
