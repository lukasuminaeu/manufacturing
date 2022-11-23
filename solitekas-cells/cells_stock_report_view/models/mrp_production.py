# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'


    location_src_id = fields.Many2one(
        'stock.location', 'Components Location',
        readonly=True,
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        states={'draft': [('readonly', False)]}, check_company=True,
        help="Location where the system will look for components.")

    # Edvardas change ADD
    # The function below gives an error 'get_warehouse()' does not exist.
    # From the code, it seems that the intent was to change stock.move
    # source location on creation/modification of move_raw_ids (components
    # in production order). If this is related to automatic transfers from
    # the warehouse stock to physical buffer zones, please refer to 
    # Umina module um_transfers_bz. I comment the onchange function below.
    # Edvardas change END

    # @api.onchange('location_src_id', 'move_raw_ids', 'routing_id')
    # def _onchange_location(self):
    #     super(MrpProduction, self)._onchange_location()
    #     for bom in self.bom_id.bom_line_ids:
    #         for move in self.move_raw_ids:
    #             if bom.product_id.id == move.product_id.id:
    #                 source_location = bom.operation_id.workcenter_id.location_id
    #                 move.update({
    #                     'warehouse_id': source_location.get_warehouse().id,
    #                     'location_id': source_location.id,
    #                 })
