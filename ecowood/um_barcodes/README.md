Umina Barcodes
--------------

Odoo Version : Odoo 15.0 Community / Enterprise


Integration
-----------

The way of use is quite simple.
In the model where you need to call an action when a barcode is read add the function *list_barcode_scanned* or the function *form_barcode_scanned*

    # For list views
    def list_barcode_scanned(self, barcode):
        action = self.env.ref('x_addon.x_action').sudo().read()[0]
        return action

    # For form views
    def form_barcode_scanned(self, barcode):
        action = self.env.ref('x_addon.x_action').sudo().read()[0]
        return action

If you need to use other function instead *list_barcode_scanned* add *barcode_action* with the function name in context.
    
    <!-- For list views -->
    <field name="context">{'barcode_action': 'other_function_scanned'}</field>
    <!-- For form views -->
    <field name="context">{'form_barcode_action': 'other_function_scanned'}</field>

    def other_function_scanned(self, barcode):
        action = self.env.ref('x_addon.x_action').sudo().read()[0]
        return action