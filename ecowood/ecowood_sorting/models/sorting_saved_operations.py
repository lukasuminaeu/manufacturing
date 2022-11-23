from odoo import api
from odoo import models, fields


class SavedOperations(models.Model):
    """
    Saved sorting operations in notebook
    4.5.1
    """
    _name = "sorting.saved.operations"
    _description = "Operations to be processed and transferred to another locations"
    operation_date = fields.Datetime("Operacijos data ir laikas", default=lambda self: fields.Datetime.now())

    type = fields.Char(string="Rūšis")
    size = fields.Float(string="Storis (mm)")
    width = fields.Float(string="Plotis (mm)")
    length1 = fields.Float(string="Ilgis (mm)")
    quantity = fields.Float(string="Vienetai")

    serial_to = fields.Char()
    square_meters = fields.Float(string="(m²)",  compute="_compute_squared_meters")

    palette_history_id = fields.Many2one("sorting.model")

    state = fields.Selection([('ready', 'Ready'),
                              ('done', 'Done'), ], string='Status',
                             default='ready', readonly=True,
                             help="ready - when scanned first time, still possible to edit. "
                                  "Done - when it's confirmed, no longer possible to edit")

    @api.depends("length1", "width")
    def _compute_squared_meters(self):
        for record in self:
            result_ = record.length1 * record.width
            result = result_ / 100 * record.quantity
            record.square_meters = result / 10000
