from odoo import api, fields, models, _


class InitiateBom(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def _create_bill_of_materials_xml(self, product_id, code, intermediate_product_id, ready_to_produce, c_class_product, w_components=False):
        vals = {
            'product_tmpl_id': self.env['product.product'].browse(product_id).product_tmpl_id.id,
            'code': code,
            'ready_to_produce': ready_to_produce,
            'product_class_c': c_class_product
        }
        bom = self.search([
            ('product_tmpl_id', '=', self.env['product.product'].browse(
                product_id).product_tmpl_id.id)
        ], limit=1)
        if bom:
            bom.write(vals)
        else:
            bom = bom.create(vals)

        if intermediate_product_id:
            bom_line_vals = {
                'product_id': intermediate_product_id,
                'bom_id': bom.id,
                'use_lot_for_finished_product': True if self.env['product.product'].browse(intermediate_product_id).tracking == 'serial' else False
            }
            bom_line = self.env['mrp.bom.line'].search([
                ('bom_id', '=', bom.id),
                ('product_id', '=', intermediate_product_id),
                ('parent_product_tmpl_id', '=', bom.product_tmpl_id.id)
            ], limit=1)
            bom_line.write(bom_line_vals) if bom_line else bom_line.create(
                bom_line_vals)

        print('create bom123')
        if w_components:
            # components = {
            # <intermediate_product_id>: {<raw_material>:<quantity>},
            # <intermediate_product_id>: {<raw_material>:<quantity>},
            # <intermediate_product_id>: {<raw_material>:<quantity>},
            # }
            # TODO: UoM. We ignore them for now because we can test without them
            components = {
                # self.env.ref('um_mrp_data.final_bifacial').id: {},
                self.env.ref('um_mrp_data.flasher_bifacial').id: {
                    self.env.ref('um_mrp_data.kampukai').id: 1,
                },
                # self.env.ref('um_mrp_data.hipot_bifacial').id: {},
                self.env.ref('um_mrp_data.backend_bifacial').id: {
                    self.env.ref('um_mrp_data.split_box_minus').id: 1,
                    self.env.ref('um_mrp_data.split_box_m').id: 1,
                    self.env.ref('um_mrp_data.split_box_plius').id: 1,
                    self.env.ref('um_mrp_data.silikono_hermetikas_juodas').id: 0.011,
                    self.env.ref('um_mrp_data.silikono_klijai_juodi').id: 0.023,
                    
                },
                self.env.ref('um_mrp_data.backend2_bifacial').id: {
                    self.env.ref('um_mrp_data.dvipuse_lipni_juosta').id: 5.65,
                    self.env.ref('um_mrp_data.juodas_aliuminio_remas_ilgas').id: 2,
                    self.env.ref(
                        'um_mrp_data.juodas_aliuminio_remas_trumpas').id: 2
                },
                self.env.ref('um_mrp_data.vizualine_patikra_bifacial').id: {},
                self.env.ref('um_mrp_data.laminavimas_bifacial').id: {
                    self.env.ref('um_mrp_data.lipni_pet_juosta').id: 6.5
                },
                self.env.ref('um_mrp_data.el_bifacial').id: {},
                self.env.ref('um_mrp_data.galinio_st_plev_bifacial').id: {
                    self.env.ref('um_mrp_data.galinis_gg').id: 1,
                    self.env.ref('um_mrp_data.priekinis_stiklas_2').id: 1.875,
                },
                self.env.ref('um_mrp_data.surinkimas_bifacial').id: {
                    self.env.ref('um_mrp_data.litavimo_juosta_plati').id: 0.04,
                    self.env.ref('um_mrp_data.coveme_label').id: 0.42,
                },
                self.env.ref('um_mrp_data.stringer_bifacial').id: {
                    self.env.ref('um_mrp_data.tongwei_m6').id: 60,
                    self.env.ref('um_mrp_data.litavimo_juosta_siaura').id: 0.168,
                    self.env.ref('um_mrp_data.litavimo_skystis').id: 0.0105,
                },
                self.env.ref('um_mrp_data.priekinis_stiklas_bifacial').id: {
                    self.env.ref('um_mrp_data.priekinis_gg').id: 1,
                    self.env.ref('um_mrp_data.priekinis_stiklas_1').id: 1.875,
                },
            }

            if components[product_id]:
                for component_id, quantity in components[product_id].items():
                    bom_line_vals = {
                        'product_id': component_id,
                        'bom_id': bom.id,
                        'product_qty': quantity,
                        'use_lot_for_finished_product': False
                    }
                    bom_line = self.env['mrp.bom.line'].search([
                        ('bom_id', '=', bom.id),
                        ('product_id', '=', component_id),
                        ('parent_product_tmpl_id', '=', bom.product_tmpl_id.id)
                    ], limit=1)
                    bom_line.write(bom_line_vals) if bom_line else bom_line.create(
                        bom_line_vals)


class InitiateWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    @api.model
    def _create_workcenter_xml(self, name, sequence, product_id, workcenter_id):
        vals = {
            'name': name,
            'bom_id': self.env['mrp.bom'].search([('product_tmpl_id', '=', self.env['product.product'].browse(product_id).product_tmpl_id.id)], limit=1).id,
            'workcenter_id': workcenter_id,
            'sequence': sequence
        }
        workcenter = self.search([
            ('bom_id', '=', vals['bom_id']),
            ('workcenter_id', '=', vals['workcenter_id'])
        ], limit=1)
        workcenter.write(vals) if workcenter else workcenter.create(vals)


class InitiateUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _create_res_user_xml(self, name, login, home_action, notif_type, workcenter, email):
        """
        We were not able to use XML data to generate users because
        technical names of access rights fields differ based
        on the order of when modules where installed.

        Here we pre-define values that are applicable
        to all workcenters. The varying values should
        be configured in um_mrp_data/data/res_users.xml
        """
        PASSWORD = 'admin'
        USER_TYPE = self.env.ref('base.group_user').id
        INVENTORY_ACCESS_RIGHTS = self.env.ref('stock.group_stock_user').id
        PURCHASE_ACCESS_RIGHTS = self.env.ref('purchase.group_purchase_user').id
        MANUFACTURING_ACCESS_RIGHTS = self.env.ref('mrp.group_mrp_manager').id
        QUALITY_ACCESS_RIGHTS = self.env.ref('quality.group_quality_manager').id
        
        menu_items_to_hide = self.env['ir.ui.menu'].search([
            ('id','not in', [
                self.env.ref('mrp.menu_mrp_workorder_todo').id, # Fullscreen workorders Kanban View
                self.env.ref('mrp.menu_mrp_root').id # Manufacturing button from the Home Screen
                ])
            ]).ids

        vals = {
            'name': name,
            'login': login,
            'password': PASSWORD,
            'action_id': home_action,
            'notification_type': notif_type,
            'workcenter_id': workcenter,
            'hide_menu_ids': [(6, 0, menu_items_to_hide)],
            'groups_id': [(6,0,[
                USER_TYPE,
                INVENTORY_ACCESS_RIGHTS,
                PURCHASE_ACCESS_RIGHTS,
                MANUFACTURING_ACCESS_RIGHTS,
                QUALITY_ACCESS_RIGHTS
            ])]
        }

        user = self.env['res.users'].search([('name','=', vals['name']),('login','=', vals['login'])], limit=1)
        if user:
            user.write(vals)
        else:
            user =self.env['res.users'].create(vals)
        user.partner_id.email = email

