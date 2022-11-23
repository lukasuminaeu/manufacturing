odoo.define('um_mrp_mps.ClientAction', function (require) {
'use strict';

const { ComponentWrapper } = require('web.OwlCompatibility');
var BarcodeEvents = require('barcodes.BarcodeEvents'); // handle to trigger barcode on bus
var session = require('web.session'); 

var core = require('web.core');
var _t = core._t;

// var concurrency = require('web.concurrency');
// var core = require('web.core');
var Dialog = require('web.Dialog');
var Pager = require('web.Pager');
var ClientAction = require('mrp_mps.ClientAction');

var QWeb = core.qweb;

const CalendarController = require('web.CalendarController');
// const ListController = require('web.ListController');
// const KanbanController = require('web.KanbanController');
const FormController = require('web.FormController');

const CalendarRenderer = require('web.CalendarRenderer');

CalendarRenderer.include({
    _getFullCalendarOptions(fcOptions) {
        let options = this._super(...arguments);
        options.weekNumberCalculation = function(date){
            // Since FullCalendar v4 ISO 8601 week date is preferred so we force the old system
            var firstdayyear_1 = moment(date.getFullYear() + '-01-01').week();
            var firstdayyear_7 = moment(date.getFullYear() + '-01-07').week();
            if (firstdayyear_1 !== firstdayyear_7) {
                return moment(date).week() + 1;
            }
            else {
                return moment(date).week();
            }
        };
        return options;
    },
});

CalendarController.include({
    start: function () {
        this._initBusNotification();
        return this._super(...arguments);
    },
    _initBusNotification: function () {
        console.log("Calendar Init Bus Notification");
        this.call('bus_service', 'onNotification', this, this._onNotification);
        this.call('bus_service', 'startPolling');
    },
    _onNotification: function (notifications) {
        var self = this;
        console.log("Is there any notification?", notifications);
        if (notifications && notifications.length !== 0) {
            notifications.forEach(function (notification) {
                if (notification.type === 'calendar_update') {
                    console.log("Calendar is updated! Refreshing.");
                    self.reload();
                }
            });
        }
    }
});

// ListController.include({
//     start: function () {
//         this._initBusNotification();
//         return this._super(...arguments);
//     },
//     _initBusNotification: function () {
//         console.log("ListController Init Bus Notification");
//         this.call('bus_service', 'onNotification', this, this._onNotification);
//         this.call('bus_service', 'startPolling');
//     },
//     _onNotification: function (notifications) {
//         var self = this;
//         console.log("Is there any notification?", notifications);
//         if (notifications && notifications.length !== 0) {
//             notifications.forEach(function (notification) {
//                 if (notification.type === 'workorder_update') {
//                     console.log("Workorders are updated! Refreshing. 5seconds");
//                     self.reload();

//                 }
//             });
//         }
//     }
// });

// KanbanController.include({
//     start: function () {
//         this._initBusNotification();
//         return this._super(...arguments);
//     },
//     _initBusNotification: function () {
//         console.log("Kanban Init Bus Notification");
//         this.call('bus_service', 'onNotification', this, this._onNotification);
//         this.call('bus_service', 'startPolling');
//     },
//     _onNotification: function (notifications) {
//         var self = this;
//         console.log("Is there any notification?", notifications);
//         if (notifications && notifications.length !== 0) {
//             notifications.forEach(function (notification) {
//                 if (notification.type === 'workorder_update') {
//                     console.log("Workorders are updated! Refreshing. 5seconds");
//                     self.reload();
//                 }
//             });
//         }
//     }
// });

FormController.include({
    start: function () {
        this._initBusNotification();
        return this._super(...arguments);
    },
    _initBusNotification: function () {
        console.log("Form Init Bus Notification");
        this.call('bus_service', 'onNotification', this, this._onNotification);
        this.call('bus_service', 'startPolling');

    },
    _onNotification: function (notifications) {
        var self = this;
        console.log("Is there any notification?", notifications);
        if (notifications && notifications.length !== 0) {

            // let is_workorder_update = notifications.some(
            //     (notif) => {
            //         return notif.type === 'workorder_update'
            //     }
            // )

            var notifications_update = notifications.filter(function (el) {
                return el.type === 'workorder_update' ||
                    el.type === 'workcenter_update'
            });

            console.log('ther123')
            console.log(notifications)
            // console.log(self['renderer']['state']['data']['workcenter_id']['data']['id'])

            // var notifications_update = notifications.filter(function (el) {
            //     return el.type === 'workorder_update' ||
            //         el.type === 'workcenter_update'
            // });

            notifications.filter(function (el) {return el.type === 'workorder_update'}).map((notif)=> {
                // Check if given product_id in payload is same as current component_id in 
                // workorder tablet view
                try {
                    let product_id = notif.payload['product_id']
                    let component_id = self['renderer']['state']['data']['component_id']['data']['id']

                    if (product_id === component_id) {
                        console.log('workorder_update, Reloading')
                        self.reload();
                    }
                }
                catch {
                    // Do nothing on error, because if we get error then whole code block stops at notification
                }
            })

            notifications.filter(function (el) {return el.type === 'workcenter_update'}).map((notif)=> {
                // Check if given product_id in payload is same as current component_id in 
                // workorder tablet view
                try {
                    let to_update_workcenter_id = notif.payload['workcenter_id']
                    let current_workcenter_id = self['renderer']['state']['data']['workcenter_id']['data']['id']

                    if (to_update_workcenter_id === current_workcenter_id) {
                        console.log('workcenter_update, Reloading')
                        self.reload();
                    }
                }
                catch {
                    // Do nothing on error, because if we get error then whole code block stops at notification
                }
            })
                

            // console.log('testąąą')
            // console.log(notifications)
            // console.log(test)

            // if (is_workorder_update) {
            //     let res_id = self['model']['loadParams']['res_id']

            //     let do_reload = false
            //     do_reload = notifications.some(
            //         (notif) => {

                // console.log(notif)
                // console.log(self)
                // console.log(notif.payload['product_id'])
                // console.log(self['rendered']['state']['data']['component_id']['data']['id'])

                        // If notification was sent with this record id, then do reload
                //         if (notif.payload === res_id)  {
                //             return
                //         }
                //     }
                // )

                // if (do_reload) {
                //     console.log('workorder_update, Reloading')
                //     self.reload();
                // }
            // }

        }
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
    _barcodeScanned: async function (barcode, target) {

        var self = this;

        return this.barcodeMutex.exec(async function () {
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
            return self.alive(Promise.all(defs)).then(async function () {

                // console.log(self['renderer']['state']['data']['finished_lot_id'])
                // console.log(barcode)
                let finished_lot_id_now = self['renderer']['state']['data']['finished_lot_id']
                let use_lot_for_finished_product = self['renderer']['state']['data']['use_lot_for_finished_product']
                let product_tracking = self['renderer']['state']['data']['product_tracking']

                // console.log('test123zzzaa1234')
                // console.log(self)
                // console.log(finished_lot_id_now)
                // console.log(use_lot_for_finished_product)

                if (
                    !use_lot_for_finished_product && finished_lot_id_now ||
                    use_lot_for_finished_product ||
                    product_tracking === 'none'
                ) {
                    let button_action = $(self.$el).find(`button[barcode_trigger="${barcode}"]`)
                    if (button_action.length > 0) {
                        button_action[0].click()
                    }
                    else {
                        // Take 'component_remaining_qty' from frontend, because in backend
                        // value didint changed when we change produced qty in tablet
                        let component_remaining_qty = parseInt(self.$el.find('span[name="component_remaining_qty"]').text())
                        
                        let workorder_id = self['renderer']['state']['data']['id']
                        let action = await self._rpc({
                            model: 'mrp.workorder',
                            method: 'barcode_scan_check_component_lot',
                            args: [workorder_id, barcode, component_remaining_qty],
                        })

                        console.log('asd123')
                        console.log(action)

                        if (action) {
                            if ('repair_workorder' in action) {
                                return self.do_action({
                                    type: 'ir.actions.act_window',
                                    res_model: 'mrp.workorder',
                                    res_id: action['repair_workorder'],
                                    target: 'current',
                                    views: [[self.viewId, 'form']],
                                });
                            }
                            else if ('button_name' in action) {
                                console.log('button name', action['button_name'])
                                let button = $(self.$el).find(`button[barcode_trigger="${action['button_name']}"]`)
                                if (button.length > 0) {
                                    button[0].click()
                                }
                            }
                        }
                    }

                    
                }

                if (!prefixed) {
                    // remember the barcode scanned for the quantity listener
                    self.current_barcode = barcode;
                    // redraw the view if we scanned a real barcode (required if
                    // we manually apply the change in JS, e.g. incrementing the
                    // quantity)
                    self.update({}, {reload: false});
                }

                
            });

        });

    },
});

const defaultPagerSize = 100;

ClientAction.include({
    events: Object.assign({}, ClientAction.prototype.events, {
        'click .o_mrp_mps_hide': '_onClickHide',
        'click .o_mrp_mps_show': '_onClickShow',
        'click .o_mrp_mps_parent_hide': '_onClickParentHide',
        'click .o_mrp_mps_parent_show': '_onClickParentShow',
        'click .o_mrp_mps_cancel_all_in_period': '_onClickCancelAllInPeriod'
    }),
    start: async function() {
        await this._super(...arguments);
        this._initBusNotification();
    },
    canBeRemoved: function () {
        console.log("MPSi canBeRemoved");
        this.call('bus_service', 'stopPolling');
        this.call('bus_service', 'deleteChannel', 'mrp_mps_channel');
        return Promise.resolve();
    },
    _initBusNotification: function () {
        console.log("MPS Init Bus Notification");
        this.call('bus_service', 'onNotification', this, this._onNotification);
        this.call('bus_service', 'startPolling');
    },
    /**
     * We listen to 'next_question' and 'end_session' events to load the next
     * page of the survey automatically, based on the host pacing.
     *
     * If the trigger is 'next_question', we handle some extra computation to find
     * a suitable "fadeInOutDelay" based on the delay between the time of the question
     * change by the host and the time of reception of the event.
     * This will allow us to account for a little bit of server lag (up to 1 second)
     * while giving everyone a fair experience on the quiz.
     *
     * e.g 1:
     * - The host switches the question
     * - We receive the event 200 ms later due to server lag
     * - -> The fadeInOutDelay will be 400 ms (200ms delay + 400ms * 2 fade in fade out)
     *
     * e.g 2:
     * - The host switches the question
     * - We receive the event 600 ms later due to bigger server lag
     * - -> The fadeInOutDelay will be 200ms (600ms delay + 200ms * 2 fade in fade out)
     *
     * @private
     * @param {Array[]} notifications structured as specified by the bus feature
     */
    _onNotification: function (notifications) {
        console.log("Is there any notification MPS?", notifications);
        var self = this;
        var mrp_source_updated = false;
        var current_products = [];

        if (notifications && notifications.length !== 0) {
            notifications.forEach(function (notification) {
                if (notification.type === 'refresh_mps') {
                    mrp_source_updated = notification;
                }
            });
        }
        if (mrp_source_updated) {
            for (var i = 0; i < self.state.length; i++) {
                var state = self.state[i];
                current_products.push(state.product_id[0]);
            };
            var products_updated = mrp_source_updated.payload.product_ids;
            var method = mrp_source_updated.payload.method;
            var needs_update = false;
            for (var j = 0; j < products_updated.length; j++) {
                if (current_products.indexOf(products_updated[j]) > -1) {
                    needs_update = true;
                    break;
                }
            }
            console.log("Needs update?", mrp_source_updated, needs_update, method, products_updated, current_products);
            if (needs_update || method === "unlink") {
                Dialog.confirm(this, "A PO/MO was updated, refresh?", {
                    confirm_callback: function () {
                        self._reloadContent();
                    },
                });
            }

        }
    },
    _onClickHide: function (ev) {
        ev.preventDefault();
        var productionScheduleId = $(ev.target).closest('.o_mps_content').data('id');
        var row = 0;
        $(ev.target).closest('.o_mps_content').find('.o_mrp_mps_show').removeClass('o_hidden');
        $(ev.target).addClass('o_hidden');
        $(ev.target).closest('.o_mps_content').find('tr').each(function(){
            var currentElement = $(this);

            if (!currentElement.hasClass("bg-light")) {
                row += 1;
                if (row != 1) currentElement.hide();
            }
        })
    },
    _onClickShow: function (ev) {
        ev.preventDefault();
        var productionScheduleId = $(ev.target).closest('.o_mps_content').data('id');
        var row = 0;
        $(ev.target).closest('.o_mps_content').find('.o_mrp_mps_hide').removeClass('o_hidden');
        $(ev.target).addClass('o_hidden');
        $(ev.target).closest('.o_mps_content').find('tr').each(function(){
            var currentElement = $(this);
            row += 1;
            if (row != 1) currentElement.show();
        })
    },
    _onClickParentHide: async function (ev) {
        ev.preventDefault();
        var productionScheduleId = $(ev.target).closest('.o_mps_content').data('id');
        var row = 0;
        $(ev.target).closest('.o_mps_content').find('.o_mrp_mps_parent_show').removeClass('o_hidden');
        $(ev.target).addClass('o_hidden');
        $(ev.target).closest('.o_mps_content').find('tr').each(function(){
            var currentElement = $(this);
            if (!currentElement.hasClass("bg-light")) {
                row += 1;
                if (row != 1) currentElement.hide();
            }
            
        });
        this.$el.find("tbody[data-group-id=" + productionScheduleId + "]").hide();

        console.log('Storing mps show/hide value in session')
        await this._rpc({
            model: 'mrp.production.schedule',
            method: 'hide_show_mps_row',
            args: [productionScheduleId, 'hide'],
        })
    },
    _onClickParentShow: async function (ev) {
        ev.preventDefault();
        var productionScheduleId = $(ev.target).closest('.o_mps_content').data('id');
        var row = 0;
        $(ev.target).closest('.o_mps_content').find('.o_mrp_mps_parent_hide').removeClass('o_hidden');
        $(ev.target).addClass('o_hidden');
        $(ev.target).closest('.o_mps_content').find('tr').each(function(){
            var currentElement = $(this);
            row += 1;
            if (row != 1) currentElement.show();
        });

        this.$el.find("tbody[data-group-id=" + productionScheduleId + "]").show();
        
        console.log('Storing mps show/hide value in session')
        await this._rpc({
            model: 'mrp.production.schedule',
            method: 'hide_show_mps_row',
            args: [productionScheduleId, 'show'],
        })

    },
    _onClickCancelAllInPeriod: function (ev) {
        ev.stopPropagation();
        var $target = $(ev.target);
        console.log("TARGET", $target);
        var dataPeriod = $target.data('period');
        console.log("dataPeriod", dataPeriod);
        this._removeQtytoReplenishInPeriod(dataPeriod);
    },
    _removeQtytoReplenishInPeriod: function (dataPeriod) {
        var self = this;
        this.mutex.exec(function () {
            return self._rpc({
                model: 'mrp.production.schedule',
                method: 'remove_replenish_orders',
                args: [false, dataPeriod],
            }).then(function () {
                return self._reloadContent();
            });
        });
    },
    renderPager: async function () {
        const currentMinimum = 1;
        const limit = defaultPagerSize;
        const size = this.recordsPager.length;

        this.pager = new ComponentWrapper(this, Pager, { currentMinimum, limit, size });

        await this.pager.mount(document.createDocumentFragment());
        const pagerContainer = Object.assign(document.createElement('span'), {
            className: 'o_mrp_mps_pager float-right',
        });
        pagerContainer.appendChild(this.pager.el);
        this.$pager = pagerContainer;

        this._controlPanelWrapper.el.querySelector('.o_cp_pager').append(pagerContainer);
    },
    _getRecordIds: function () {
        var self = this;
        return this._rpc({
            model: 'mrp.production.schedule',
            method: 'search_read',
            domain: this.domain,
            fields: ['id'],
        }).then(function (ids) {
            self.recordsPager = ids;
            self.active_ids = ids.slice(0, defaultPagerSize).map(i => i.id);
        });
    },

    _createProduct: function () {
        var self = this;
        var exitCallback = function () {
            return self._rpc({
                model: 'mrp.production.schedule',
                method: 'search_read',
                args: [[], ['id']],
                limit: 1,
                orderBy: [{name: 'id', asc: false}]
            }).then(function (result) {
                if (result.length) {
                    window.location.reload();
                    //return self._renderProductionSchedule(result[0].id);
                }
            });
        };
        this.mutex.exec(function () {
            return self.do_action('mrp_mps.action_mrp_mps_form_view', {
                on_close: exitCallback,
            });
        });
    },
    
    _renderState: function (states) {
        for (var i = 0; i < states.length; i++) {
            var state = states[i];

            var $table = $(QWeb.render('mrp_mps_production_schedule', {
                manufacturingPeriods: this.manufacturingPeriods,
                state: [state],
                groups: this.groups,
                formatFloat: this.formatFloat,
                
            }));
            var $tbody = $('.o_mps_content[data-id='+ state.id +']');
            if ($tbody.length) {
                $tbody.replaceWith($table);
            } else {
                var $warehouse = false;
                if ('warehouse_id' in state) {
                    $warehouse = $('.o_mps_content[data-warehouse_id='+ state.warehouse_id[0] +']');
                }
                if ($warehouse.length) {
                    $warehouse.last().after($table);
                } else {
                    $('.o_mps_product_table').append($table);
                }
            }
        }
        this._update_cp_buttons();
        return Promise.resolve();
    },
});

return ClientAction;

});
