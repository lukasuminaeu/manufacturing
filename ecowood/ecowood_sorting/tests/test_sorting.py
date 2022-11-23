# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestSorting(TransactionCase):

    def setUp(self):
        super(TestSorting, self).setUp()

        # Get created products
        self.not_sorted_product = self.env.ref('ecowood_sorting.item_unsorted_lamels')
        self.sorted_product = self.env.ref("ecowood_sorting.item_sorted_lamels")

        self.stock_location = self.env.ref("um_lots.work_location_warehouse")

    def test_calibration(self):
        unsorted_lot_display_name = "KALIBRATED"
        item_calibrated = self.env.ref('um_lots.item_dried_boards_calibrated_product_template')

        lot = self.env['stock.production.lot'].create({
            'name': unsorted_lot_display_name,
            'product_id': item_calibrated.id,
            'company_id': self.env.company.id,
        })

        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': item_calibrated.id,
            'lot_id': lot.id,
            'inventory_quantity': 1111
        })

        self.assertEqual(inventory_quant.quantity, 0)
        self.assertEqual(inventory_quant.inventory_diff_quantity, 1111)

        inventory_quant.action_apply_inventory()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(item_calibrated, self.stock_location,
                                                                         lot_id=lot), 1111.0)

    def test_sorting_volume(self):
        lot = self.env['stock.production.lot'].create({
            'name': "test volume",
            'product_id': self.sorted_product.id,
            'company_id': self.env.company.id,
            'thickness': 100,
            'width': 200,
            'length1': 300,
        })

        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.sorted_product.id,
            'lot_id': lot.id,
            'inventory_quantity': 100
        })

        inventory_quant.action_apply_inventory()

        self.assertEqual(inventory_quant.volume, 0.6)

    def test_sorting_lot(self):
        unsorted_lot_display_name = "001UNSORTED"
        unsorted_pallet_price = 1000
        unsorted_thickness = 1
        unsorted_width = 2
        unsorted_length = 3
        unsorted_type = "01TYPE"

        sorted_lot_display_name_1 = "SORTEDTEST1"
        sorted_pallet_price = 0
        sorted_thickness = 0
        sorted_width = 0
        sorted_length = 0

        lot1_unsorted = self.env['stock.production.lot'].create({
            'name': unsorted_lot_display_name,
            'product_id': self.not_sorted_product.id,
            'company_id': self.env.company.id,
            'palette_price': unsorted_pallet_price,
            'thickness': unsorted_thickness,
            'width': unsorted_width,
            'length1': unsorted_length,
            'type_of': unsorted_type,
        })

        lot1_sorted = self.env['stock.production.lot'].create({
            'name': sorted_lot_display_name_1,
            'product_id': self.sorted_product.id,
            'company_id': self.env.company.id,
        })

        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.not_sorted_product.id,
            'lot_id': lot1_unsorted.id,
            'inventory_quantity': 1000
        })

        self.assertEqual(inventory_quant.quantity, 0)
        self.assertEqual(inventory_quant.inventory_diff_quantity, 1000)

        inventory_quant.action_apply_inventory()
        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.not_sorted_product, self.stock_location,
                                                                         lot_id=lot1_unsorted), 1000.0)
        self.assertEqual(
            len(self.env['stock.quant']._gather(self.not_sorted_product, self.stock_location, lot_id=lot1_unsorted)),
            1.0)
        self.assertEqual(lot1_unsorted.product_qty, 1000.0)
        self.assertEqual(lot1_unsorted.name, unsorted_lot_display_name)

        # Operation type: PERVRUS
        self.sent_to_sorting_stock_move(lot1_unsorted)

        # Testing sorted.model
        sorting_model = self.env['sorting.model'].search([("serial_number", "=", unsorted_lot_display_name)])
        self.assertEqual(sorting_model.quantity, lot1_unsorted.product_qty)
        self.assertEqual(sorting_model.fixed_total_price, unsorted_pallet_price)
        self.assertEqual(sorting_model.width, unsorted_width)
        self.assertEqual(sorting_model.size, unsorted_thickness)
        self.assertEqual(sorting_model.width, unsorted_width)
        self.assertEqual(sorting_model.length1, unsorted_length)
        self.assertEqual(sorting_model.type_of, unsorted_type)

        # Transfer 400 elements from unsorted lot to sorted
        for element in range(4):
            self.env['sorting.saved.operations'].create({
                "palette_history_id": sorting_model.id,
                "state": "ready",
                "quantity": 100,
                "serial_to": lot1_sorted.name
            })
        sorting_model.action_transfer_sorted()
        self.assertEqual(sorting_model.sorted_lamels, 400)
        for completed_pallets in sorting_model.palette_ids:
            self.assertEqual(completed_pallets.state, "done")
        self.assertEqual(lot1_sorted.product_qty, 400)

        # Check initial price
        for transfer in lot1_sorted.transferred_stock_move_ids:
            self.assertEqual(transfer.average_price, 1)

        # Recalculate average price
        # TODO: change to calculate m^2
        # sorting_model.end_timer()
        # for transfer in lot1_sorted.transferred_stock_move_ids:
        #     self.assertEqual(transfer.average_price, 2.5)

    def sent_to_sorting_stock_move(self, lot1_unsorted):
        """
        Create transfer from client code
        Operation Type: Pervežimas į Rusiavimą:
        Source Location 	WH/Stock/Sandėlys
        Destination Location: 	WH/Stock/Rušiavimas/IN
        :param lot1_unsorted:
        """
        picking_type_sorting_in_out = self.env.ref(
            "ecowood_sorting.operation_type_transfer_to_sorting")  # Operation type: PERVRUS
        order_line = (0, 0,
                      {
                          'product_id': self.not_sorted_product.id,  # Nerušiuotos lameles
                          'lot_id': lot1_unsorted.id,
                          'product_uom': self.not_sorted_product.uom_id.id,
                          'company_id': self.env.user.company_id.id,
                          'name': self.not_sorted_product and self.not_sorted_product.name or self.not_sorted_product.product_id.name,
                          'location_id': picking_type_sorting_in_out.default_location_src_id.id,  # Rušiavimas IN
                          'location_dest_id': picking_type_sorting_in_out.default_location_dest_id.id,  # Rušiavimas OUT
                          'product_uom_qty': 1000,
                      }
                      )
        self.picking_id = self.env['stock.picking'].create({
            'picking_type_id': picking_type_sorting_in_out.id,
            'location_id': picking_type_sorting_in_out.default_location_src_id.id,
            'location_dest_id': picking_type_sorting_in_out.default_location_dest_id.id,
            'move_lines': [order_line],
            'move_type': 'direct',
        })
        self.picking_id.action_confirm()
        self.picking_id.move_lines[0].quantity_done = 1000.0
        self.picking_id.action_assign()
        self.picking_id.button_validate()
