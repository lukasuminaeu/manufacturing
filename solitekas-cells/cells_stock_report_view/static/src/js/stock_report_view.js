odoo.define('cells_stock_report_view.StockReportView', function (require) {
'use strict';

var concurrency = require('web.concurrency');
var core = require('web.core');
var AbstractAction = require('web.AbstractAction');
var Dialog = require('web.Dialog');
var field_utils = require('web.field_utils');
var session = require('web.session');

var QWeb = core.qweb;
var _t = core._t;

var ClientAction = AbstractAction.extend({
    contentTemplate: 'srv_template',
    hasControlPanel: true,
    loadControlPanel: true,
    withSearchBar: true,
    events: {
        'click .o_select_work_center': '_onClickWorkCenter',
        'change .js_days_demand': '_onChangeDemand',
    },
    init: function (parent, action) {
        this._super.apply(this, arguments);
        this.actionManager = parent;
        this.action = action;
        this.context = action.context;
        this.domain = [];
        this.component_ids = [];
        this.resource_name = '';
        this.resource_id = false;
        this.demand = 5;
        this.formatFloat = field_utils.format.float;
        this.state = false;
        this.mutex = new concurrency.Mutex();
        this.controlPanelParams.modelName = 'stock.report.view';
    },
    willStart: function () {
        var self = this;
        var _super = this._super.bind(this);
        var args = arguments;
        var def_content = this._getState();
        var def_control_panel = this._rpc({
            model: 'ir.model.data',
            method: 'get_object_reference',
            args: ['cells_stock_report_view', 'stock_report_view_search_view'],
            kwargs: {context: session.user_context},
        }).then(function (viewId) {
            self.controlPanelParams.viewId = viewId[1];
        });
        return Promise.all([def_content, def_control_panel]).then(function () {
            return _super.apply(self, args);
        });
    },
    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.update_cp();
        });
    },
    _getState: function () {
        var self = this;
        return this._rpc({
            model: 'stock.report.view',
            method: 'get_view_state',
            args: [this.domain],
        }).then(function (state) {
            self.state = state.resource_ids;
            return state;
        });
    },
    update_cp: function () {
        var self = this;
        var resources = {resources: self.state};
        this.$buttons = $(QWeb.render('StockReportView.buttons', resources));
        this.updateControlPanel({
            title: _t('Stock Analysis'),
            cp_content: {
                $buttons: this.$buttons,
                // $searchview_buttons: this.$searchview_buttons
            },
        });
        $('.js_days_demand').val(this.demand);

        if (self.state.length == 0) {
            this.$buttons.addClass('d-none');
        }
    },
    _onClickWorkCenter: function (ev) {
        ev.stopPropagation();
        var self = this;
        var work_center_id = $(ev.target).attr('data-id');
        var days = parseInt($('.js_days_demand').val());
        var demand_in_days;
        if (days > 0) {
            demand_in_days = days;
            this.demand = demand_in_days;
        }

        return this._rpc({
            model: 'stock.report.view',
            method: 'get_component_data',
            args: [work_center_id, demand_in_days],
        }).then(function (result) {
            if (result) {
                // console.log(result);
                self.component_ids = result.component_ids;
                self.resource_name = result.work_center_name;
                self.resource_id = result.work_center_id;
                return self._reloadContent();
            } else {
                return self._reloadContent();
            }
        });
    },
    _reloadContent: function () {
        var self = this;
        var msg = 'Reloads';
        return this._getState().then(function () {
            var $content = $(QWeb.render('srv_template', {
                widget: {
                    component_ids: self.component_ids,
                    resource_name: self.resource_name,
                    resource_id: self.resource_id,
                    state: self.state,
                }
            }));
            $('.o_srv_resource').replaceWith($content);
            self.update_cp();
        });
    },
    _onChangeDemand: function (ev) {
        ev.stopPropagation();
        var self = this;
        var work_center_id = $('.o_resource_id').attr('resource-id');
        var days = parseInt($('.js_days_demand').val());
        var demand_in_days;
        if (days > 0) {
            demand_in_days = days;
            this.demand = demand_in_days;
        }
        if (work_center_id) {

            return this._rpc({
                model: 'stock.report.view',
                method: 'get_component_data',
                args: [work_center_id, demand_in_days],
            }).then(function (result) {
                if (result) {
                    self.component_ids = result.component_ids;
                    self.resource_name = result.work_center_name;
                    self.resource_id = result.work_center_id;
                    self._reloadContent();
                } else {
                    self._reloadContent();
                }
            });
        }
    },
});
core.action_registry.add('stock_report_view_action', ClientAction);
return ClientAction;
});