odoo.define('um_barcodes.list', function (require) {
'use strict';

var ListController = require('web.ListController');
var concurrency = require('web.concurrency');
var core = require('web.core');

ListController.include({
    custom_events: _.extend({}, ListController.prototype.custom_events, {
        activeBarcode: '_barcodeActivated',
    }),
    init: function (parent, model, renderer, params) {
        console.log("Working listcontroller");
        this._super.apply(this, arguments);

        this.barcodeMutex = new concurrency.Mutex();
        this._barcodeStartListening();
    },
    /**
     * @override
     */
    destroy: function () {
        this._barcodeStopListening();
        this._super();
    },
    /**
     * @private
     */
    _barcodeStartListening: function () {
        core.bus.on('barcode_scanned', this, this._barcodeScanned);
    },
    /**
     * @private
     */
    _barcodeStopListening: function () {
        core.bus.off('barcode_scanned', this, this._barcodeScanned);
    },
    /**
     * Method called when a user scan a barcode, call each method in function of the
     * widget options then update the renderer
     *
     * @private
     * @param {string} barcode sent by the scanner (string generate from keypress series)
     * @param {DOM Object} target
     * @returns {Promise}
     */
    _barcodeScanned: function (barcode, target) {
        var self = this;
        this.barcode_action = (typeof this.initialState.context.barcode_action === 'undefined') ? "list_barcode_scanned" : this.initialState.context.barcode_action;
        return this.barcodeMutex.exec(function () {
            return self._rpc({
                model: self.modelName,
                method: self.barcode_action,
                args: [false, barcode],
                context: self.initialState.context
            }).then(function (action){
                if (typeof action === 'undefined') {
                    console.log("Barcode read but there is no function in model for an action", barcode);
                }
                else {
                    console.log(action)
                    if (!action.views) {
                       return self.do_action(action);
                    }

                    action.views = action.views.map((view) => [view[0], view[1] === "tree" ? "list" : view[1]]);
                    return self.do_action(action);
                }

            });
        });
    },
});

});
