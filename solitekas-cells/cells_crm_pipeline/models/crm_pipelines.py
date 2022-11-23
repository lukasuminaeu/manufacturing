from odoo import api, fields, models, tools
import logging

_logger = logging.getLogger(__name__)


class CrmLeadCellsPipeline(models.Model):
    _name = 'crm.cells.pipeline'
    _description = 'cells pipelines categories for teams'

    name = fields.Char('Pipeline name')