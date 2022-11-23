odoo.define('um_stock_receipt.many2one_fastcreate', function (require) {
"use strict";

var field_registry = require('web.field_registry');
require('web._field_registry');
var basic_fields = require('web.basic_fields');
var relational_fields = require('web.relational_fields');

const { _t } = require('web.core');
const { sprintf, toBoolElse } = require("web.utils");

/**
 * Override the Many2One to open a dialog in mobile.
 */
var FieldMany2oneFastCreate = relational_fields.FieldMany2One.extend({
    template: "FieldMany2oneFastCreate",
    events: _.extend({}, relational_fields.FieldMany2One.prototype.events, {
        'click .o_barcode_mobile': '_onBarcodeButtonClick',
    }),
    init: function () {
        this._super.apply(this, arguments);
        this._setFastCreate();
    },
    _setFastCreate: function () {
        var fastcreateField = this.nodeOptions.fastcreate || this.field.fastcreate || 'fastcreate';

        this.nextField = this.nodeOptions.next_field || self.name;
        this.fastCreate = this.record.data[fastcreateField];
    },
    _onInputKeyup: function (ev) {
        if (this.fastCreate && (ev.which === $.ui.keyCode.ENTER || ev.which === $.ui.keyCode.TAB)) {
            // If we pressed enter or tab, we want to prevent _onInputFocusout from
            // executing since it would open a M2O dialog to request
            // confirmation that the many2one is not properly set.
            // It's a case that is already handled by the autocomplete lib.
            return;
        }
        else {
            this._super.apply(this, arguments);
        }
    },
    _search: async function (searchValue = "") {

        const self = this;
        const value = searchValue.trim();
        const domain = this.record.getDomain(this.recordParams);
        const context = Object.assign(
            this.record.getContext(this.recordParams),
            this.additionalContext
        );

        // Exclude black-listed ids from the domain
        const blackListedIds = this._getSearchBlacklist();
        if (blackListedIds.length) {
            domain.push(['id', 'not in', blackListedIds]);
        }

        const nameSearch = this._rpc({
            model: this.field.relation,
            method: "name_search",
            kwargs: {
                name: value,
                args: domain,
                operator: "ilike",
                limit: this.limit + 1,
                context,
            }
        });
        const results = await this.orderer.add(nameSearch);

        // Format results to fit the options dropdown
        let values = results.map((result) => {
            const [id, fullName] = result;
            const displayName = this._getDisplayName(fullName).trim();
            result[1] = displayName;
            return {
                id,
                label: escape(displayName) || data.noDisplayContent,
                value: displayName,
                name: displayName,
            };
        });

        // Add "Search more..." option if results count is higher than the limit
        if (this.limit < values.length) {
            values = this._manageSearchMore(values, value, domain, context);
        }

        // Additional options...
        const canQuickCreate = this.can_create && !this.nodeOptions.no_quick_create;
        const canCreateEdit = this.can_create && !this.nodeOptions.no_create_edit;
        if (value.length) {
            // "Quick create" option
            const nameExists = results.some((result) => result[1] === value);

            if (this.fastCreate && !nameExists) {
                clearTimeout(this.fill_timeout);
                this.fill_timeout = setTimeout(function() {
                    self._fastCreate(value).then(function(){
                        self.$el.parents( ".o_selected_row" ).find('input[name=' + self.nextField + ']').focus().select();
                    });
                }, 400);
                return []
            };

            if (this.fastCreate && nameExists) {
                clearTimeout(this.fill_timeout);
                let confirmAction = confirm("This record already exists, do you want to select it?");
                if (confirmAction) {
                    self.reinitialize({id: values[0].id, display_name: values[0].label});
                }
                else {
                    self.reinitialize({id: false, display_name: name});
                }
            }

            if (canQuickCreate && !nameExists) {
                values.push({
                    label: sprintf(
                        _t(`Create "<strong>%s</strong>"`),
                        escape(value)
                    ),
                    action: () => this._quickCreate(value),
                    classname: 'o_m2o_dropdown_option'
                });
            }
            // "Create and Edit" option
            if (canCreateEdit) {
                const valueContext = this._createContext(value);
                values.push({
                    label: _t("Create and Edit..."),
                    action: () => {
                        // Input value is cleared and the form popup opens
                        this.el.querySelector(':scope input').value = "";
                        return this._searchCreatePopup('form', false, valueContext);
                    },
                    classname: 'o_m2o_dropdown_option',
                });
            }
            // "No results" option
            if (!values.length) {
                values.push({
                    label: _t("No records"),
                    classname: 'o_m2o_no_result',
                });
            }
        } else if (!this.value && (canQuickCreate || canCreateEdit)) {
            // "Start typing" option
            values.push({
                label: _t("Start typing..."),
                classname: 'o_m2o_start_typing',
            });
        }
        return values;
    },
    _fastCreate: function (name) {
        var self = this;
        var createDone;

        var slowCreate = function () {
            var dialog = self._searchCreatePopup("form", false, self._createContext(name));
            dialog.on('closed', self, createDone);
        };

        var def = new Promise(function (resolve, reject) {
            self.createDef = new Promise(function (innerResolve) {
                // called when the record has been quick created, or when the dialog has
                // been closed (in the case of a 'slow' create), meaning that the job is
                // done
                createDone = function () {
                    innerResolve();
                    resolve();
                    self.createDef = undefined;
                };
            });

            const prom = self.reinitialize({id: false, display_name: name});
            prom.guardedCatch(reason => {
                reason.event.preventDefault();
                slowCreate();
            });
            self.dp.add(prom).then(createDone).guardedCatch(reject);
        });

        return def;
    },

    /**
     * @override
     */
    start: function () {
        var result = this._super.apply(this, arguments);
        this.fill_timeout = null;
        return result;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * External button is visible
     *
     * @return {boolean}
     * @private
     */
    _isExternalButtonVisible: function () {
        return this.$external_button.is(':visible');
    },
    /**
     * Hide the search more option
     *
     * @param {Array} values
     */
    _manageSearchMore(values) {
        return values;
    },
});

var FieldOne2manyBoolean = basic_fields.FieldBoolean.extend({
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        this.one2manyField = this.nodeOptions.one2many_field || self.name;
    },
    _setValue: function (value, options) {
        var self = this;
        var fieldsInfo = this.record.fieldsInfo['form'];
        var fields2 = this.recordData[self.one2manyField];
        if (value) {
            var fieldNext = fieldsInfo[self.one2manyField];
            //fields2.trigger_up('add_record');
            //fieldNext.Widget.trigger_up('add_record');
        };
        return this._super(value, options);
    },
});

field_registry
    .add('many2one_fastcreate', FieldMany2oneFastCreate)
    .add('switch_one2many_boolean', FieldOne2manyBoolean);

return FieldMany2oneFastCreate;
});
