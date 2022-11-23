# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pickup_time_from = fields.Char(string='Delay alert contract outdated', default=30,
                                   config_parameter='dpd.pickup_time_from',
                                   help="Desired pickup time interval – starting time (HH:mm) Minutes should be either 00 or 30. There can be interval restrictions that can be affected by country and ZIP code. Request should be submitted at least 15 minutes before pickup time.")
    pickup_time_to = fields.Char(string='Delay alert contract outdated', default=30,
                                 config_parameter='dpd.pickup_time_to',
                                 help="Desired pickup time interval – final time (HH:mm) Minutes should be either 00 or 30. There can be interval restrictions that can be affected by country and ZIP code.")

    is_production = fields.Boolean(string='Production',
                                   config_parameter='dpd.is_production',
                                   help="True - production. False - testnet ")

