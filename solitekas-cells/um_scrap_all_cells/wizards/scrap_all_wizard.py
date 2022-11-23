from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

class ScrapAllWizard(models.TransientModel):
    _name = 'scrap.all.wizard'

    stock_scrap_lines = fields.One2many('stock.scrap.line', 'scrap_all_wizard')

    package_id = fields.Many2one(
        'stock.quant.package', 'Package',
        check_company=True)
    owner_id = fields.Many2one('res.partner', 'Owner', check_company=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    
    def _get_default_location_id(self):
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        return None

    location_id = fields.Many2one(
        'stock.location', 'Source Location', domain="[('usage', '=', 'internal'), ('company_id', 'in', [company_id, False])]",
        required=True, default=_get_default_location_id, check_company=True)

    def _get_default_scrap_location_id(self):
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        return self.env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [company_id, False])], limit=1).id

    scrap_location_id = fields.Many2one(
        'stock.location', 'Scrap Location', default=_get_default_scrap_location_id,
        domain="[('scrap_location', '=', True), ('company_id', 'in', [company_id, False])]", required=True, check_company=True)

    @api.onchange('scrap_location_id')
    def _onchange_scrap_location_id(self):
        for record in self:
            for ln in record.stock_scrap_lines:
                ln.scrap_location_id = record.scrap_location_id.id

    @api.model
    def default_get(self, fields_list):
        res = super(ScrapAllWizard, self).default_get(fields_list)
        vals = []
        # For all bom lines, get default lines of components that will be scraped for current produced product
        mo = self.env['mrp.production'].browse([self._context['default_production_id']])
        line_index = 0
        for idx, stock_move in enumerate(mo.move_raw_ids):
            #component qty required to produce product
            required_qty = stock_move.bom_line_id.product_qty
            #registered compoents is the ones that is already registered to produce product
            registered_components = stock_move.move_line_ids.filtered(lambda x: x.qty_done > 0)
            #unregistered components is that is not assigned to product yet
            unregistered_components = stock_move.move_line_ids.filtered(lambda x: x.qty_done == 0)
            
            #Take all registered components and isert into scrap all table
            if registered_components:
                for ln in registered_components:
                    if ln.qty_done:
                        obj = {
                            'product_id': ln.product_id.id, 
                            'scrap_qty': ln.qty_done,
                            'related_stock_move': stock_move.id,
                            'scrap_location_id': res['scrap_location_id'] if 'scrap_location_id' in res else False,
                            'lot_id': ln.lot_id.id
                        }
                        vals.append((0, line_index, obj))
                        line_index += 1
                        required_qty -= ln.qty_done
            #If there is unregistered components that will still be used in product, then include them too
            for ln in unregistered_components:
                if required_qty > 0:
                    available_ln_qty = ln.product_uom_qty - ln.qty_done
                    # if this line and lot has enough qty for scrapping
                    if float_compare(required_qty, available_ln_qty, precision_rounding=stock_move.product_uom.rounding) < 0:
                        obj = {
                            'product_id': ln.product_id.id, 
                            'scrap_qty': required_qty,
                            'related_stock_move': stock_move.id,
                            'scrap_location_id': res['scrap_location_id'] if 'scrap_location_id' in res else False,
                            'lot_id': ln.lot_id.id
                        }
                        vals.append((0, line_index, obj))
                        line_index += 1
                        required_qty -= required_qty
                    else:
                        obj = {
                            'product_id': ln.product_id.id, 
                            'scrap_qty': available_ln_qty,
                            'related_stock_move': stock_move.id,
                            'scrap_location_id': res['scrap_location_id'] if 'scrap_location_id' in res else False,
                            'lot_id': ln.lot_id.id
                        }
                        vals.append((0, line_index, obj))
                        line_index += 1
                        required_qty -= available_ln_qty

        res.update({'stock_scrap_lines': vals})
        return res


    def action_validate(self):
        self.ensure_one()
        # First iterate through lines to see if there is sufficient quantity to scrap in needed location
        insufficient_products_to_scrap_error = _('Insufficient Quantity To Scrap:') + '\n'
        qty_components_error = ''
        error_msg1 = False
        error_msg2 = False
        for prod_to_scrap in self.stock_scrap_lines:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            available_qty = sum(self.env['stock.quant']._gather(prod_to_scrap.product_id,
                                                                self.location_id,
                                                                prod_to_scrap.lot_id,
                                                                self.package_id,
                                                                self.owner_id,
                                                                strict=True).mapped('quantity'))
            
            scrap_qty = prod_to_scrap.product_id.uom_id._compute_quantity(prod_to_scrap.scrap_qty, prod_to_scrap.product_id.uom_id)
            
            if float_compare(available_qty, scrap_qty, precision_digits=precision) < 0:
                insufficient_products_to_scrap_error += prod_to_scrap.product_id.display_name + ' ' + str(prod_to_scrap.scrap_qty) + ' ' + prod_to_scrap.product_id.uom_id.name + '\n'
                error_msg1 = True

        mo = self.env['mrp.production'].browse([self._context['default_production_id']])
        # check if there isnt too much or too less quantities selected to scrap current product
        for stock_move in mo.move_raw_ids:
            required_qty = stock_move.bom_line_id.product_qty
            lines = self.stock_scrap_lines.filtered(lambda x: x.product_id.id == stock_move.product_id.id)
            if float_compare(required_qty, sum(lines.mapped('scrap_qty')), precision_digits=precision) < 0:
                qty_components_error += (_("Too much components to scrap for component ") + stock_move.product_id.name + ":\n" + str(sum(lines.mapped('scrap_qty'))) + _(" is given, while it needs ") + str(required_qty) + '\n')
                error_msg2 = True
            elif float_compare(required_qty, sum(lines.mapped('scrap_qty')), precision_digits=precision) > 0:
                qty_components_error += (_("Not enough components to scrap for component ") + stock_move.product_id.name + ":\n" + str(sum(lines.mapped('scrap_qty'))) + _(" is given, while it needs ") + str(required_qty) + '\n')
                error_msg2 = True

        if error_msg1:
            raise UserError(insufficient_products_to_scrap_error)
        if error_msg2:
            raise UserError(qty_components_error)

        # If there is enough quantities, do the scrap for every scrap line
        for prod_to_scrap in self.stock_scrap_lines:
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            available_qty = sum(self.env['stock.quant']._gather(prod_to_scrap.product_id,
                                                                self.location_id,
                                                                prod_to_scrap.lot_id,
                                                                self.package_id,
                                                                self.owner_id,
                                                                strict=True).mapped('quantity'))
            scrap_qty = prod_to_scrap.product_id.uom_id._compute_quantity(prod_to_scrap.scrap_qty, prod_to_scrap.product_id.uom_id)
            
            if prod_to_scrap.product_id.type != 'product' or float_compare(available_qty, scrap_qty, precision_digits=precision) >= 0:
                return self.um_do_scrap()


    def um_do_scrap(self):
        self.ensure_one()
        self._check_company()

        mo = self.env['mrp.production'].browse([self._context['default_production_id']])
        mo_wo = self._context['active_model'] == 'mrp.workorder' and self.env['mrp.workorder'].browse([self._context['active_id']])
        
        #'if not mo.is_scrapped' because it was doing these scraps two times for somewhat reason
        if not mo.is_scrapped:
            for idx, scrap_line in enumerate(self.stock_scrap_lines):
                name = self.env['ir.sequence'].next_by_code('stock.scrap') or _('New')
                stock_scrap = self.env['stock.scrap'].create({
                    'product_id': scrap_line.product_id.id,
                    'scrap_qty': scrap_line.scrap_qty,
                    'lot_id': scrap_line.lot_id.id,
                    'name': name,
                    'location_id': self.location_id.id,
                    # Theres a glitch, that it doesnt get default value that is set from scrap_location_id in stock_scrap_line 
                    #with the reason that i dont know, so if it is not set manually by hand, just use the scrap_location_id that is set
                    #in scrap record
                    # 'scrap_location_id': scrap_line.scrap_location_id.id,
                    'scrap_location_id': scrap_line.scrap_location_id and scrap_line.scrap_location_id.id or scrap.scrap_location_id.id,
                    # 'package_id': self.package_id.id,
                    'product_uom_id': scrap_line.uom_id.id
                })
                
                move = self.env['stock.move'].create(stock_scrap._prepare_move_values())
                # master: replace context by cancel_backorder
                move.with_context(is_scrap=True)._action_done()

                # substract qty of scrapped components from MO move lines qty_done field
                mo_stock_line = scrap_line.related_stock_move.move_line_ids.filtered( \
                    lambda x: x.lot_id == scrap_line.lot_id \
                        and x.qty_done >= scrap_line.scrap_qty
                )
                if mo_stock_line:
                    mo_stock_line.qty_done -= scrap_line.scrap_qty

                stock_scrap.write({'move_id': move.id, 'state': 'done'})
                stock_scrap.date_done = fields.Datetime.now()
        
            #If theres more than one product produced, then split MO's, cancel and etc... Same way as it 
            #would be by producing products
            backorder = False
            if mo.product_qty > 1:
                #When scrap is for product, set current MO as canceled and create backorder
                #This method splits MO
                backorder = mo._generate_backorder_productions(close_mo=False)
                #Set qty to 1
                mo.product_qty = mo.qty_producing

            #Cancel MO
            mo.action_cancel()
            #Add boolean field, to know wheter this MO was scrapped
            mo.is_scrapped = True

            self._close_repair_order()

            if mo.product_qty > 1:
                if backorder:
                    for wo in (mo | backorder).workorder_ids:
                        if wo.state in ('done', 'cancel'):
                            continue
                        wo.current_quality_check_id.update(wo._defaults_from_move(wo.move_id))
                        if wo.move_id:
                            wo._update_component_quantity()
                    if not self.env.context.get('no_start_next'):
                        if mo_wo.operation_id:
                            return backorder.workorder_ids.filtered(lambda wo: wo.operation_id == mo_wo.operation_id).open_tablet_view()
                        else:
                            index = list(mo.workorder_ids).index(mo_wo)
                            return backorder.workorder_ids[index].open_tablet_view()
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'mrp.production',
                    'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                    'res_id': mo.id,
                    'target': 'main',
                }

        return True
    
    def _close_repair_order(self):
        """If origin model that scrap was called from is 'repair.order'
        then close it after scrap is completed"""
        if self._context['active_model'] == 'repair.order':
            repair_order = self.env['repair.order'].browse(self._context['active_ids'])
            if repair_order:
                repair_order.action_repair_cancel()