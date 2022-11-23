# -*- coding: utf-8 -*-


{
    'name': "Elgras",

    'summary': """Užsakymų valdymo sprendimas""",

    'description': """
        Užsakymų valdymo sprendimas, DPD integracija
    """,

    'author': "Unima",
    'website': "https://www.umina.eu/",

    'category': 'Customizations',
    

    'version': '0.7.7',

    
    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'stock', 'delivery', 'sale_management', 'um_product_pictures',
                'export_product_image_app', 'um_stock_barcode', 'mail_optional_follower_notification'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/quotations_partner_platform_view.xml',
        'views/invoices_crm_tab_view.xml',
        'views/contacts_add_field_view.xml',

        'views/dpd_tab_button_view.xml',
        'views/dpd_receits_tab_view.xml',
        'views/dpd_documents_tab_in_quotations_view.xml',
        'views/dpd_enable_button_stock_view_location_form_inherit_view.xml',
        'data/ir_config_parameter_data_dpd.xml',

        # 'report/report.xml',
        'report/elgras_mail_template_data_send_carrier.xml',
        'report/elgras_mail_template_invoice.xml',
        'report/elgras_mail_template_sale_order.xml',
        'report/elgras_mail_template_data_from_warehouse.xml',

        'views/dpd_move_line_popup_fields_view.xml',
        'data/dpd_cron_daily_check_automation.xml',
        'data/dpd_cron_bearer_check.xml',

        # Add DPD..etc tags to Quotations
        'views/quotations_inventory_column_tags.xml',

        # Change Invoice report add fields
         'report/credit_note.xml',

        # Config settings for dpd courier pick up
        'views/res_config_settings_views.xml',

        # Extend stock.quant.package to show package id from dpd
        'views/stock_quant_package_extend.xml',

    ],
    # Enable this to app to be displayed
    'application': True,
    # 'sequence': -1,
    'license': 'LGPL-3',

}
