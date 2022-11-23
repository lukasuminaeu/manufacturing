/** @odoo-module **/
import BarcodeModel from '@stock_barcode/models/barcode_model';
import { _t } from 'web.core';
import { patch } from 'web.utils';
var Dialog = require('web.Dialog');

patch(BarcodeModel.prototype, 'um_stock_barcode/static/src/models/barcode_model.js', {
    async updateLine(line, args) {
        let {lot_id, owner_id, package_id} = args;
        if (!line) {
            throw new Error('No line found');
        }
        console.log('here213zz')
        console.log(line.product_id)
        console.log(args.product_id)
        if (!line.product_id && args.product_id) {
            line.product_id = args.product_id;
            line.product_uom_id = this.cache.getRecord('uom.uom', args.product_id.uom_id);
        }

        console.log('here213zzaaa')
        console.log(line.product_id)
        console.log(args.product_id)

        // line.product_id = {
        //     "id": 2084,
        //     "barcode": false,
        //     "default_code": "JB07GG",
        //     "detailed_type": "product",
        //     "tracking": "lot",
        //     "display_name": "[SPLIT JBOX 0] Jungties dezute stiklas stiklas moduliui (0)",
        //     "uom_id": 1,
        //     "proposed_package_quantity": 25
        // }

        if (lot_id) {
            if (typeof lot_id === 'number') {
                lot_id = this.cache.getRecord('stock.production.lot', args.lot_id);
            }
            line.lot_id = lot_id;
        }
        if (owner_id) {
            if (typeof owner_id === 'number') {
                owner_id = this.cache.getRecord('res.partner', args.owner_id);
            }
            line.owner_id = owner_id;
        }
        if (package_id) {
            if (typeof package_id === 'number') {
                package_id = this.cache.getRecord('stock.quant.package', args.package_id);
            }
            line.package_id = package_id;
        }
        if (args.lot_name) {
            await this.updateLotName(line, args.lot_name);
        }

        // If args is not 'package' but its 'product', only then initiate below function
        if ('package_id' in args == false || ('package_id' in args && !args['package_id'])) {
            // This conditional here , to not throw error if product couldnt be found
            if ('lot_id' in args && 'product_id' in args['lot_id']) {
                // Umina edit: here we will calculate all possible qty for product in location with that lot,
                // and then assign all possible qty if there is any 
                let newQtyDone = await this.getMaximumQtyLotLocation(args)
                args['qty_done'] = newQtyDone
            }
        }

        this._updateLineQty(line, args);
        this._markLineAsDirty(line);
    },

    async getMaximumQtyLotLocation (args) {
        // qty_done will consist of currently reserved qties in stock move plus
        // all the available qties found in stock.quant with location and lot
        let filter_lines = this['currentState']['lines'].filter((x)=>{
            return x['product_id']['id'] == args['lot_id']['product_id'] 
            && x['lot_id']['id'] == args['lot_id']['id']
        })

        console.log('max132')
        console.log(args)
        console.log(args['lot_id']['product_id'])
        console.log(args['lot_id']['id'])

        let lines_reserved_qty = filter_lines.reduce((n, {product_uom_qty}) => n + product_uom_qty, 0)
        
        let response = await this.orm.call("stock.quant", 'search_read', [
            [
                ['product_id', '=', args['lot_id']['product_id']],
                ['lot_id', '=', args['lot_id']['id']],
                ['location_id', '=', this.currentLocationId],
            ],
            [
                'available_quantity',
            ]
        ])
        let available_qty_in_stock = response.reduce((n, {available_quantity}) => n + available_quantity, 0)
        let qty_done = 0
        qty_done = lines_reserved_qty + available_qty_in_stock
        return qty_done
    },

    async um_get_product_obj_from_scanned_lot(barcodeData) {
        // This function will try to get product obj information from scanned lot information so that according
        // line would be created insted of: standard odoo functioning of adding lot line that even doesnt exist.
        let lot_id = await this.um_get_lot_id_by_lot_name(barcodeData['barcode'])

        let product_info = false
        if (lot_id) {

            let product_info = await this.orm.call("product.product", 'search_read', [
                [
                    ['id', '=', lot_id['product_id'][0]],
                ],
                [
                    'id', 'barcode', 'default_code', 'detailed_type', 'tracking', 'display_name', 'uom_id', 'proposed_package_quantity',
                ]
            ])
            product_info[0]['uom_id'] = product_info[0]['uom_id'][0]
            return product_info[0]
        }
        
        return product_info
    },

    /**
     * Starts by parse the barcode and then process each type of barcode data.
     *
     * @param {string} barcode
     * @returns {Promise}
     */
     async _processBarcode(barcode) {

        console.log('test here123')
        console.log(this.isDialogOpen)
        if (this.isDialogOpen) {
            return
        }
        console.log('continue process1')
        let barcodeData = {};
        let currentLine = false;
        // Creates a filter if needed, which can help to get the right record
        // when multiple records have the same model and barcode.
        const filters = {};
        if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
            filters['stock.production.lot'] = {
                product_id: this.selectedLine.product_id.id,
            };
        }
        try {
            barcodeData = await this._parseBarcode(barcode, filters);
            console.log('???')
            console.log(barcodeData)
        } catch (parseErrorMessage) {
            barcodeData.error = parseErrorMessage;
        }

        // Process each data in order, starting with non-ambiguous data type.
        if (barcodeData.action) { // As action is always a single data, call it and do nothing else.
            return await barcodeData.action();
        }

        console.log('here12321bbbaa')
        // console.log(barcodeData.product)
        console.log(barcodeData.packaging)

        if (barcodeData.packaging) {
            barcodeData.product = this.cache.getRecord('product.product', barcodeData.packaging.product_id);
            barcodeData.quantity = barcodeData.packaging.qty;
            barcodeData.uom = this.cache.getRecord('uom.uom', barcodeData.product.uom_id);
        }
        console.log(barcodeData.packaging)

        // if (barcodeData.lot && !barcode.product) {
        //     barcodeData.product = this.cache.getRecord('product.product', barcodeData.lot.product_id);
        // }

        console.log(barcodeData.product)

        await this._processLocation(barcodeData);
        await this._processPackage(barcodeData);
        console.log('package123', barcodeData.packaging)
        if (barcodeData.stopped) {
            // TODO: Sometime we want to stop here instead of keeping doing thing,
            // but it's a little hacky, it could be better to don't have to do that.
            return;
        }

        if (barcodeData.weight) { // Convert the weight into quantity.
            barcodeData.quantity = barcodeData.weight.value;
        }

        // If no product found, take the one from last scanned line if possible.
        if (!barcodeData.product) {
            // Umina edit: new function to get product obj information for lot scanned, that it would look
            // for product by lot name, instead of creating new line lots for product that even doesnt HashChangeEvent
            // that lots in system at all.
            let product_obj_information = await this.um_get_product_obj_from_scanned_lot(barcodeData)
            if (product_obj_information) {
                barcodeData.product = product_obj_information
                barcodeData.lotName = barcodeData['barcode'];
            }
            console.log('quantity123')
            console.log(product_obj_information)

            // if (barcodeData.quantity) {
            //     currentLine = this.selectedLine || this.lastScannedLine;
            // } else if (this.selectedLine && this.selectedLine.product_id.tracking !== 'none') {
            //     currentLine = this.selectedLine;
            // } else if (this.lastScannedLine && this.lastScannedLine.product_id.tracking !== 'none') {
            //     currentLine = this.lastScannedLine;
            // }
            // if (currentLine) { // If we can, get the product from the previous line.
            //     const previousProduct = currentLine.product_id;
            //     // If the current product is tracked and the barcode doesn't fit
            //     // anything else, we assume it's a new lot/serial number.
            //     if (previousProduct.tracking !== 'none' &&
            //         !barcodeData.match && this.canCreateNewLine) {
            //         barcodeData.lotName = barcode;
            //     }
            //     if (currentLine.lot_id || currentLine.lot_name ||
            //         barcodeData.lot || barcodeData.lotName ||
            //         barcodeData.quantity) {
            //         barcodeData.product = previousProduct;
            //     }
            // }
        }

        const {product} = barcodeData;
        console.log('product123')
        console.log(product)
        if (!product) { // Product is mandatory, if no product, raises a warning.
            if (!barcodeData.error) {
                if (this.groups.group_tracking_lot) {
                    barcodeData.error = _t("You are expected to scan one or more products or a package available at the picking location");
                } else {
                    barcodeData.error = _t("You are expected to scan one or more products.");
                }
            }
            return this.notification.add(barcodeData.error, { type: 'danger' });
        }
        if (barcodeData.weight) { // the encoded weight is based on the product's UoM
            barcodeData.uom = this.cache.getRecord('uom.uom', product.uom_id);
        }

        // Default quantity set to 1 by default if the product is untracked or
        // if there is a scanned tracking number.
        if (product.tracking === 'none' || barcodeData.lot || barcodeData.lotName || this._incrementTrackedLine()) {
            barcodeData.quantity = barcodeData.quantity || 1;
            if (product.tracking === 'serial' && barcodeData.quantity > 1 && (barcodeData.lot || barcodeData.lotName)) {
                barcodeData.quantity = 1;
                this.notification.add(
                    _t(`A product tracked by serial numbers can't have multiple quantities for the same serial number.`),
                    { type: 'danger' }
                );
            }
        }

        // Searches and selects a line if needed.
        if (!currentLine || this._shouldSearchForAnotherLine(currentLine, barcodeData)) {
            currentLine = this._findLine(barcodeData);
        }

        if ((barcodeData.lotName || barcodeData.lot) && product) {
            const lotName = barcodeData.lotName || barcodeData.lot.name;
            for (const line of this.currentState.lines) {
                if (line.product_id.tracking === 'serial' && this.getQtyDone(line) !== 0 &&
                    ((line.lot_id && line.lot_id.name) || line.lot_name) === lotName) {
                    return this.notification.add(
                        _t("The scanned serial number is already used."),
                        { type: 'danger' }
                    );
                }
            }
            // Prefills `owner_id` and `package_id` if possible.
            const prefilledOwner = (!currentLine || (currentLine && !currentLine.owner_id)) && this.groups.group_tracking_owner && !barcodeData.owner;
            const prefilledPackage = (!currentLine || (currentLine && !currentLine.package_id)) && this.groups.group_tracking_lot && !barcodeData.package;
            if (this.useExistingLots && (prefilledOwner || prefilledPackage)) {
                const lotId = (barcodeData.lot && barcodeData.lot.id) || (currentLine && currentLine.lot_id && currentLine.lot_id.id) || false;
                const res = await this.orm.call(
                    'product.product',
                    'prefilled_owner_package_stock_barcode',
                    [product.id],
                    {
                        lot_id: lotId,
                        lot_name: (!lotId && barcodeData.lotName) || false,
                    }
                );
                this.cache.setCache(res.records);
                if (prefilledPackage && res.quant && res.quant.package_id) {
                    console.log('qq111')
                    console.log(res.quant.package_id)
                    
                    console.log(barcodeData.package)
                    barcodeData.package = this.cache.getRecord('stock.quant.package', res.quant.package_id);
                    console.log(barcodeData.package)
                }
                if (prefilledOwner && res.quant && res.quant.owner_id) {
                    barcodeData.owner = this.cache.getRecord('res.partner', res.quant.owner_id);
                }
            }
        }

        // Updates or creates a line based on barcode data.
        if (currentLine) { // If line found, can it be incremented ?
            let exceedingQuantity = 0;
            if (product.tracking !== 'serial' && barcodeData.uom && barcodeData.uom.category_id == currentLine.product_uom_id.category_id) {
                // convert to current line's uom
                barcodeData.quantity = (barcodeData.quantity / barcodeData.uom.factor) * currentLine.product_uom_id.factor;
                barcodeData.uom = currentLine.product_uom_id;
            }
            if (this.canCreateNewLine) {
                // Checks the quantity doesn't exceed the line's remaining quantity.
                if (currentLine.product_uom_qty && product.tracking === 'none') {
                    const remainingQty = currentLine.product_uom_qty - currentLine.qty_done;
                    if (barcodeData.quantity > remainingQty) {
                        // In this case, lowers the increment quantity and keeps
                        // the excess quantity to create a new line.
                        exceedingQuantity = barcodeData.quantity - remainingQty;
                        barcodeData.quantity = remainingQty;
                    }
                }
            }
            if (barcodeData.quantity > 0) {
                console.log('now123')
                console.log(barcodeData.lotName)
                console.log(barcodeData.lot)
                const fieldsParams = this._convertDataToFieldsParams({
                    qty: barcodeData.quantity,
                    lotName: barcodeData.lotName,
                    lot: barcodeData.lot,
                    package: barcodeData.package,
                    owner: barcodeData.owner,
                });
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                console.log('currentline1')
                console.log(currentLine)
                console.log(fieldsParams)
                await this.updateLine(currentLine, fieldsParams);
            }
            if (exceedingQuantity) { // Creates a new line for the excess quantity.
                console.log('test111zz')
                console.log(barcodeData)
                console.log(barcodeData.lot)
                console.log(barcodeData.lotName)
                const fieldsParams = this._convertDataToFieldsParams({
                    product,
                    qty: exceedingQuantity,
                    lotName: barcodeData.lotName,
                    lot: barcodeData.lot,
                    package: barcodeData.package,
                    owner: barcodeData.owner,
                });
                if (barcodeData.uom) {
                    fieldsParams.uom = barcodeData.uom;
                }
                console.log('here222??')

                currentLine = await this._createNewLine({
                    copyOf: currentLine,
                    fieldsParams,
                });
                this.checkIfQtyToPack(currentLine)

                console.log('????12233')
            }
        } else if (this.canCreateNewLine) { // No line found. If it's possible, creates a new line.

            console.log('test222zz')
            console.log(barcodeData.lot)
            console.log(barcodeData.lotName)

            let test = await this.um_get_lot_id_by_lot_name(barcodeData.lotName)

            console.log('asd123z')
            console.log(test)
            if (test) {
                barcodeData.lotName = undefined
                barcodeData.lot = test
                barcodeData.lot['product_id'] = test['product_id'][0]
            }

            const fieldsParams = this._convertDataToFieldsParams({
                product,
                qty: barcodeData.quantity,
                lotName: barcodeData.lotName,
                lot: barcodeData.lot,
                package: barcodeData.package,
                owner: barcodeData.owner,
            });
            if (barcodeData.uom) {
                fieldsParams.uom = barcodeData.uom;
            }

            console.log(this.currentLocationId)
            console.log('product122')
            console.log(this)
            console.log(product)

            console.log('qq111zz')
            console.log(this.currentLocationId)
            console.log(product['id'])
            let test1 = await this.orm.call("stock.quant", 'search_read', [
                [
                    ['location_id', '=', this.currentLocationId],
                    ['product_id', '=', product['id']],
                ],
                ['available_quantity']
            ])

            let sum_available_qty = test1.reduce((n, {available_quantity}) => n + available_quantity, 0)

            // Only create line, if quantity is more than zero
            if (sum_available_qty > 0) {
                currentLine = await this._createNewLine({fieldsParams});

                this.checkIfQtyToPack(currentLine)
                

                // console.log(product)
                // console.log(barcodeData)
                // console.log(sum_available_qty)
                // console.log(this)

            }
        }
        // And finally, if the scanned barcode modified a line, selects this line.
        if (currentLine) {
            this.selectLine(currentLine);
        }
        this.trigger('update');
    },

    checkIfQtyToPack(currentLine) {

        // Check if qty to pack is reached, if so throw popup confirming to pack these lots
        console.log('here12233')
        console.log(currentLine)
        let currentLineProductId = currentLine['product_id']['id']
        console.log(currentLineProductId)
        console.log(this.pageLines)

        if (currentLine['product_id']['tracking'] === 'serial') {
            let getLinesProductId = this.pageLines.filter(function (line) {
                if (line['product_id']['id'] === currentLineProductId) {
                    if ('result_package_id' in line === false) {
                        return line
                    }
                    else if ('result_package_id' in line === true && !line['result_package_id']) {
                        return line
                    }
                }
                
            })
            let totalLinesQty = getLinesProductId.reduce((n, {qty_done}) => n + qty_done, 0)
    
            console.log('totalLinesQty', totalLinesQty)
    
            console.log('get123')
            console.log(getLinesProductId)
            
            if (totalLinesQty >= currentLine['product_id']['proposed_package_quantity']) {
                this.packingConfirmBox();

                // setTimeout(() => {
                //     let confirmAction = confirm("PROPOSED PACKAGE QUANTITY REACHED. Confirm if you want to form the package, cancel if you want to continue scanning.");
                //     if (confirmAction) {
                //         this._putInPack();
                //     };
                // }, 500);
            }
        }
        
    },

    packingConfirmBox() {
        self = this;
        // This variable 'isDialogOpen' is used to not let keep scanning lots,
        // if dialog is open and waiting for answer
        self.isDialogOpen = true;
        Dialog.confirm(this, (("Pasiektas supakavimo kiekis. Ar norite supakuoti produktus?")), {
            confirm_callback: function () {
                self._putInPack();
                self.isDialogOpen = false;
            },
            cancel_callback: function () {
                console.log('cancel_callback')
                self.isDialogOpen = false;
            },
        });
    },



    async um_get_lot_id_by_lot_name(lotname) {
        let lot_id = await this.orm.call("stock.production.lot", 'search_read', [
            [['name', '=', lotname]],
            ['id', 'name', 'ref', 'product_id']
        ])
        
        let latest_lot_id = false
        if (lot_id.length > 0) {
            latest_lot_id = lot_id.reduce(function(prev, current) {
                return (prev['id'] > current['id']) ? prev : current
            })
            console.log(latest_lot_id)
        } 

        return latest_lot_id
    }
});


    

