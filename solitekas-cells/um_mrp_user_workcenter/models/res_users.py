
from odoo import models, fields, _, api


class ResUsers(models.Model):
    _inherit = "res.users"

    workcenter_id = fields.Many2one("mrp.workcenter", "Workcenter")