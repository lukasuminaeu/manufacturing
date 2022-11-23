from odoo import models, fields


class StockPicking(models.Model):
    """
    Saved work time in notebook
    """
    _name = "sorting.saved.time"
    _description = "saving time model to store work hours"
    work_started = fields.Datetime(string="Darbo pradžia")
    work_ended = fields.Datetime(string="Darbo pabaiga")
    worker = fields.Many2one("res.users", string="Darbuotojas")
    notes = fields.Char(string="Pastabos")
    work_time = fields.Float(string="Darbo trukmė", digits=(16, 2), help="Time spent")

    work_time_id = fields.Many2one("sorting.model")
