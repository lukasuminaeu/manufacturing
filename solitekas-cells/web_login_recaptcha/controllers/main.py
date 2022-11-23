import requests
from odoo.addons.web.controllers.main import Home, ensure_db

from odoo import http, _
from odoo.http import request

LOGIN_PARAM = 'login_google_recaptcha'
SITE_KEY_PARAM = 'google_recaptcha_site_key'
SECRET_KEY_PARAM = 'google_recaptcha_secret_key'


def verify_recaptcha(captcha_data):
    r = requests.post('https://www.google.com/recaptcha/api/siteverify', captcha_data)
    return r.json()


class HomeRecaptcha(Home):
    @http.route()
    def web_login(self, redirect=None, **kw):
        ensure_db()
        params = request.env['ir.config_parameter'].sudo()
        login_recaptcha = params.get_param(LOGIN_PARAM)
        recaptcha_site_key = params.get_param(SITE_KEY_PARAM)
        request.params.update({
            'login_recaptcha': login_recaptcha,
            'recaptcha_site_key': recaptcha_site_key
        })

        if request.httprequest.method == 'POST' and login_recaptcha:
            is_captcha_verified = False
            if recaptcha_site_key:
                values = request.params.copy()
                captcha_data = {
                    'secret': params.get_param(SECRET_KEY_PARAM),
                    'response': request.params['field-recaptcha-response'],
                }

                response = verify_recaptcha(captcha_data)
                is_captcha_verified = response.get('success')

            if not is_captcha_verified:
                values['error'] = _("Invalid reCaptcha")
                response = request.render('web.login', values)
                response.headers['X-Frame-Options'] = 'DENY'
                return response

        return super(HomeRecaptcha, self).web_login(redirect=redirect, **kw)
