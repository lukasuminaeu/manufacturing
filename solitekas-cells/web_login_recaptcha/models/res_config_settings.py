from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    login_google_recaptcha = fields.Boolean(string="Login Recaptcha")
    google_recaptcha_site_key = fields.Char(string="Google Recaptcha Site Key")
    google_recaptcha_secret_key = fields.Char(string="Google Recaptcha Secret Key")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(login_google_recaptcha=params.get_param('login_google_recaptcha'),
                   google_recaptcha_site_key=params.get_param('google_recaptcha_site_key'),
                   google_recaptcha_secret_key=params.get_param('google_recaptcha_secret_key'))
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('login_google_recaptcha', self.login_google_recaptcha)
        params.set_param('google_recaptcha_site_key', self.google_recaptcha_site_key)
        params.set_param('google_recaptcha_secret_key', self.google_recaptcha_secret_key)
