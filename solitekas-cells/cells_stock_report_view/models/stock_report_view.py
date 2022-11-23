# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models, _
from datetime import date, datetime, timedelta


import logging
_logger = logging.getLogger(__name__)


class StockReportView(models.Model):
    _name = 'stock.report.view'
    _description = 'Stock Report View'

    @api.model
    def get_view_state(self, domain=False):
        work_center_obj = self.env['mrp.workcenter']
        work_order_obj = self.env['mrp.workorder']
        resource_ids = []
        for work_center in work_center_obj.search(domain):
            if work_center:
                states = ('state', 'in', ('ready', 'progress'))
                domain = [('workcenter_id', '=', work_center.id), states]
                orders = work_order_obj.search(domain).ids
                if orders:
                    resource_ids.append({'id': work_center.id, 'name': work_center.name})
        return {
            'resource_ids': resource_ids,
        }

    @api.model
    def get_component_data(self, work_center_id, demand_in_days):
        component_ids, list_ids = [], []

        today = datetime.today().date()
        date_behind = today + timedelta(days=demand_in_days)

        domain = [('workcenter_id', '=', int(work_center_id)), ('state', 'in', ('ready', 'progress'))]
        work_order_obj = self.env['mrp.workorder'].search(domain)

        orders = work_order_obj.filtered(lambda x: today <= x.date_planned_start.date() <= date_behind)

        for order in orders.raw_workorder_line_ids:
            order_lines = orders.raw_workorder_line_ids.filtered(lambda x: x.product_id.id == order.product_id.id)
            qty_reserved = sum(x.qty_reserved for x in order_lines)

            if order_lines.product_id.id not in list_ids:
                list_ids.append(order_lines.product_id.id)
                location_id = order_lines.move_id.location_id

                variant = order_lines.product_id.product_template_attribute_value_ids._get_combination_name()
                name = variant and "%s (%s)" % (order_lines.product_id.name, variant) or order_lines.product_id.name

                component_ids.append({
                    'id': order_lines.product_id.id,
                    'default_code': order_lines.product_id.default_code,
                    'name': name,
                    # 'name': '[%s] %s' % (order_lines.product_id.default_code, order_lines.product_id.name),
                    'location': location_id.complete_name,
                    'qty_available': self.get_available_quantity(order_lines.product_id, location_id),
                    'rules': self.get_min_max_qty(order_lines.product_id, location_id),
                    'qty_reserved': qty_reserved,
                    'action_needed': self.action_needed(order_lines.product_id, location_id, qty_reserved),
                })

        # _logger.debug('\n\n%s\n', component_ids)
        return {
            'component_ids': component_ids,
            'work_center_name': work_order_obj[0].workcenter_id.name,
            'work_center_id': work_order_obj[0].workcenter_id.id,
        }

    def get_available_quantity(self, product_id, location_id):
        domain = [('product_id', '=', product_id.id), ('location_id', '=', location_id.id)]
        quant_obj = self.env['stock.quant'].search(domain)
        return quant_obj.quantity if quant_obj else 0

    def get_min_max_qty(self, product_id, location_id):
        rules = []
        domain = [('product_id', '=', product_id.id), ('location_id', '=', location_id.id)]
        point_obj = self.env['stock.warehouse.orderpoint'].search(domain, order='id asc', limit=1)
        if point_obj:
            for record in point_obj:
                if record:
                    rules.append({
                        'name': record.name,
                        'location_id': record.location_id.complete_name,
                        'product_id': record.product_id.id,
                        'product_min_qty': record.product_min_qty,
                        'product_max_qty': record.product_max_qty,
                    })
            return rules
        else:
            return [{
                'product_min_qty': '-',
                'product_max_qty': '-',
            }]

    def action_needed(self, product_id, location_id, demand):
        product = self.env['product.product'].browse(product_id.id)
        domain = [('product_id', '=', product_id.id), ('location_id', '=', location_id.id)]
        point_obj = self.env['stock.warehouse.orderpoint'].search(domain, order='id asc', limit=1)
        product_min_qty = point_obj.product_min_qty
        product_max_qty = point_obj.product_max_qty
        on_hand = self.get_available_quantity(product, location_id)

        if not product_min_qty and not product_max_qty:
            if on_hand == demand:
                return False
            if on_hand > demand:
                return [{'action': 'out', 'qty': on_hand - demand}]
            else:
                return [{'action': 'in', 'qty': demand - on_hand}]
        else:
            if on_hand < demand:
                qty = (product_max_qty - product_min_qty) + (demand - on_hand)
                return [{'action': 'in', 'qty': qty}]
            else:
                qty = (on_hand - demand)
                if qty > product_max_qty:
                    return [{'action': 'out', 'qty': qty - product_max_qty}]
                if qty < product_min_qty:
                    qty -= product_min_qty
                    return [{'action': 'out', 'qty': qty * -1 if qty < 0 else qty}]
                if product_min_qty < qty < product_max_qty:
                    return False
