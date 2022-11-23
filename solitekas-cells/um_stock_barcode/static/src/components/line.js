/** @odoo-module **/

import LineComponent from '@stock_barcode/components/line';
import {patch} from 'web.utils';
import {useService} from "@web/core/utils/hooks";

patch(LineComponent.prototype, 'um_stock_barcode', {
    setup() {
        this._super.apply(this, arguments);
        this.orm = useService("orm");
    },
    async printPackageSlip() {
        const action = {
            type: "ir.actions.act_url",
            url: `/um_stock_barcode/pdf/` + this.props.line.result_package_id.id,
        };
        await this.trigger('do-action', {action});
    },
    addQuantity(quantity, ev) {
        var proposed_package_quantity = this.line.product_id.proposed_package_quantity;
        var group_lines = this.env.model.groupedLines[0].lines

        let quantity_done = 0
        if (group_lines && group_lines.length >= 1) {
            for (const line_id of group_lines) {
                quantity_done += line_id['qty_done']
            }
            // if (quantity_done + quantity === proposed_package_quantity && this.line.result_package_id === false) {
            //     this.env.model.updateLineQtyandPack(this.line.virtual_id, quantity);
            // } else {
                this.env.model.updateLineQty(this.line.virtual_id, quantity);
            // }

        }
        // else if (this.line.qty_done + quantity === proposed_package_quantity && this.line.result_package_id === false) {
        //     this.env.model.updateLineQtyandPack(this.line.virtual_id, quantity);
        // } 
        else {
            this.env.model.updateLineQty(this.line.virtual_id, quantity);
        }
    },
});