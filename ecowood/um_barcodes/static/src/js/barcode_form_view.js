odoo.define('um_barcodes.form', function (require) {
'use strict';

var FormController = require('web.FormController');
var BarcodeEvents = require('barcodes.BarcodeEvents'); // handle to trigger barcode on bus

FormController.include({
    _barcodeScanned: function (barcode, target) {
        var self = this;
        console.log("self")
        console.log(self)
        var record = this.model.get(this.handle);
        return this.barcodeMutex.exec(function () {
            var prefixed = _.any(BarcodeEvents.ReservedBarcodePrefixes,
                    function (reserved) {return barcode.indexOf(reserved) === 0;});
            var hasCommand = false;
            var defs = [];
            if (! $.contains(target, self.el)) {
                return;
            }
            for (var k in self.activeBarcode) {
                var activeBarcode = self.activeBarcode[k];
                // Handle the case where there are several barcode widgets on the same page. Since the
                // event is global on the page, all barcode widgets will be triggered. However, we only
                // want to keep the event on the target widget.
                var methods = self.activeBarcode[k].commands;
                var method = prefixed ? methods[barcode] : methods.barcode;
                if (method) {
                    if (prefixed) {
                        hasCommand = true;
                    }
                    defs.push(self._barcodeActiveScanned(method, barcode, activeBarcode));
                }
            }
            if (prefixed && !hasCommand) {
                self.displayNotification({ title: _t('Undefined barcode command'), message: barcode, type: 'danger' });
            }
            if (!prefixed) {
                self.barcode_action = (typeof self.initialState.context.form_barcode_action === 'undefined') ? "form_barcode_scanned" : self.initialState.context.form_barcode_action;
                return self._rpc({
                    model: self.modelName,
                    method: self.barcode_action,
                    args: [record.res_id, barcode],
                    context: self.initialState.context
                }).then(function (action){
                    if (typeof action === 'undefined') {
                        console.log("Barcode read but there is no function in model for an action", barcode);
                    }
                    else {
                    if (!action.views) {
                        // fix confirm sorting transactions view
                       return self.do_action(action);
                    }
                        action.views = action.views.map((view) => [view[0], view[1] === "tree" ? "list" : view[1]]);
                        return self.do_action(action);
                    }

                });
            }
            return self.alive(Promise.all(defs)).then(function () {
                if (!prefixed) {
                    // remember the barcode scanned for the quantity listener
                    self.current_barcode = barcode;
                    // redraw the view if we scanned a real barcode (required if
                    // we manually apply the change in JS, e.g. incrementing the
                    // quantity)
                    self.update({}, {reload: true});
                }
            });
        });
    },
});

});
