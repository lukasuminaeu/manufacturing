from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta

class UminaWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    # def button_scrap_multiple(self):
    #     self.ensure_one()
    #     """
    #         Edvardas change: the client decided to make 'Scrap All' button
    #         easy, that is, after they press 'Scrap All', the production
    #         order is marked as 'to_be_scrapped'. On call of record_production
    #         method, Odoo will:
    #             1) consume all materials (it will 'produce' the final product),
    #             2) scrap final product (because it will detect 'to_be_scrapped'),
    #             3) reduce all source production orders by 1 ('discount_source_qty' method)
            
    #         If product has returned from repair, then we immediately delete production
    #         order and direct user to the kanban view, because it means the user is working
    #         on a dummy production order whose lot_id has already been produced. This means,
    #         that the order should not make it to the 'record_production' function
    #         because it will raise an error.
            
    #     """
    #     # 'needs_repairing': False  is important because you cannot
    #     # repair product that will be scrapped
    #     self.production_id.write({'needs_repairing': False})
    #     self.production_id.write({'to_be_scrapped': True})
    #     if self.production_id.has_returned_from_repair:
    #         if not self.production_id._check_repairing():
    #             self.production_id.unlink()
    #             return self.env['mrp.workorder'].um_mrp_workorder_todo()

    def button_scrap_multiple(self):
        """ 
        'Scrap all' functionality:
            For production that produces product which is tracked by serial numbers:
                1) Find all already registered components and process them through scrap process;
                2) Create backorder for this production order;
                3) Cancel current production order because it was scrapped and discount source qty.
        """
        for record in self:
            #Create backorder
            backorder_qty = record.production_id.product_qty - 1 
            amounts = {self: [1, backorder_qty]}
            self.production_id._split_productions(amounts)

            #Find already registered components and scrap them.
            for wo_move in record.move_raw_ids:
                for wo_move_line in wo_move.move_line_ids:
                    if wo_move_line.qty_done:
                        stock_scrap_obj = record.env['stock.scrap']
                        stock_scrap = stock_scrap_obj.create({
                            'product_id': wo_move_line.product_id.id,
                            'product_uom_id': wo_move_line.product_id.uom_id.id,
                            'scrap_qty': wo_move_line.qty_done,
                            'lot_id': wo_move_line.lot_id.id,
                            'production_id': record.production_id.id,
                            'workorder_id': record.id,
                            'location_id': record.production_id.location_src_id.id,
                        })
                        stock_scrap.with_context(scrap_all=True).action_validate()

            #Cancel current production and discount source qty.
            self.production_id._action_cancel()
            self.discount_source_qty()