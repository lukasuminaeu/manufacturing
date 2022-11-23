odoo.define('barcodes.ecowood_barcode.FormView', function (require) {
"use strict";

var BarcodeEvents = require('barcodes.BarcodeEvents'); // handle to trigger barcode on bus
var concurrency = require('web.concurrency');
var core = require('web.core');
var Dialog = require('web.Dialog');
var FormController = require('web.FormController');
var FormRenderer = require('web.FormRenderer');


FormController.include({
    /**
     * add default barcode commands for from view
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);

        this.activeBarcode = {
            form_view: {
                commands: {
                    'O-CMD.EDIT': this._barcodeEdit.bind(this),
                    'O-CMD.DISCARD': this._barcodeDiscard.bind(this),
                    'O-CMD.SAVE': this._barcodeSave.bind(this),
                    'O-CMD.PREV': this._barcodePagerPrevious.bind(this),
                    'O-CMD.NEXT': this._barcodePagerNext.bind(this),
                    'O-CMD.PAGER-FIRST': this._barcodePagerFirst.bind(this),
                    'O-CMD.PAGER-LAST': this._barcodePagerLast.bind(this),
                    'O-CMD.CONFIRM': this._assign_validate.bind(this),
                    'O-CMD.TEST': this._assign_test.bind(this),

                },
            },
        };

        this.barcodeMutex = new concurrency.Mutex();
        this._barcodeStartListening();
    },


   /**
     * @private
     */
    _assign_test: async function () {
//        this.saveRecord();


        var self = this;
        return this._rpc({
                model: "stock.picking",
                method: "action_kalibration_view",
                args: [""],
                context: this.initialState.context,
            }).then(function (result) {
                self.do_action(result);
            });

    },


    /**
     * @private
     */
    _assign_validate: async function () {
        this.saveRecord();

        let picking_id = this.initialState.data.picking_id.res_id

        const ecowood_assign_confirm_picking = await this._rpc({
            args: [picking_id],
            method: 'ecowood_assign_confirm_picking',
            model: 'stock.picking',
        });

        var self = this;
        return this._rpc({
                model: "stock.picking",
                method: "action_kalibration_view",
                args: [""],
                context: this.initialState.context,
            }).then(function (result) {
                self.do_action(result);
            });



    },
});

});
