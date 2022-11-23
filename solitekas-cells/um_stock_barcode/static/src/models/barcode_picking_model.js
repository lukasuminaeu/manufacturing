/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { patch } from 'web.utils';


patch(BarcodePickingModel.prototype, 'um_stock_barcode', {
    // updateLineQtyandPack(virtualId, qty = 1) {
    //     console.log('here??11')
    //     var self = this;
    //     this.actionMutex.exec(() => {
    //         const line = this.pageLines.find(l => l.virtual_id === virtualId);
    //         this.updateLine(line, {qty_done: qty});
    //         this.trigger('update');
    //     }).then(function (){
    //         setTimeout(() => {
    //             let confirmAction = confirm("PROPOSED PACKAGE QUANTITY REACHED. Confirm if you want to form the package, cancel if you want to continue scanning.");
    //             if (confirmAction) {
    //                 self._putInPack();
    //             };
    //         }, 500);
    //     });


    // },

    getIncrementQuantity(line) {
        // Umina edit: changed it to not use Math.max, because if we wanted
        // to click button for example 0.011 demand , it was still making qty
        // done to 1 instead of 0.011.
        let buttonDemand = this.getQtyDemand(line) - this.getQtyDone(line)
        return buttonDemand
        // return Math.max(this.getQtyDemand(line) - this.getQtyDone(line), 1);
    },

    _updateLineQty(line, args) {
        if (line.product_id.tracking === 'serial' && line.qty_done > 0 && (this.record.use_create_lots || this.record.use_existing_lots)) {
            return;
        }
        if (args.qty_done) {
            if (args.uom) {
                // An UoM was passed alongside the quantity, needs to check it's
                // compatible with the product's UoM.
                const lineUOM = line.product_uom_id;
                if (args.uom.category_id !== lineUOM.category_id) {
                    // Not the same UoM's category -> Can't be converted.
                    const message = sprintf(
                        _t("Scanned quantity uses %s as Unit of Measure, but this UoM is not compatible with the line's one (%s)."),
                        args.uom.name, lineUOM.name
                    );
                    return this.notification.add(message, { title: _t("Wrong Unit of Measure"), type: 'danger' });
                } else if (args.uom.id !== lineUOM.id) {
                    // Compatible but not the same UoM => Need a conversion.
                    args.qty_done = (args.qty_done / args.uom.factor) * lineUOM.factor;
                    args.uom = lineUOM;
                }
            }

            // Umina edit: we will be setting qty instead of adding up
            line.qty_done = args.qty_done;
            // line.qty_done += args.qty_done;
        }
    }

});
