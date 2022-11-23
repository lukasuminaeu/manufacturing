/** @odoo-module **/

import MainComponent from '@stock_barcode/components/main';
import { patch } from 'web.utils';
import { useService} from "@web/core/utils/hooks";

// Owl Render
const { Component, hooks } = owl;
const { useState, onWillStart, onMounted } = hooks;

patch(MainComponent.prototype, '/ecowood_barcode/static/src/components/main.js', {

    async willStart() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");

        console.log("running willStart")
        console.log(this)
        const barcodeData = await this.rpc(
            '/stock_barcode/get_barcode_data',
            {
                model: this.props.model,
                res_id: this.props.id || false,
            }
        );
        this.groups = barcodeData.groups;
        this.env.model.setData(barcodeData);
        this.env.model.on('process-action', this, this._onDoAction);
        this.env.model.on('notification', this, this._onNotification);
        this.env.model.on('refresh', this, this._onRefreshState);
        this.env.model.on('update', this, this.render);
        this.env.model.on('do-action', this, args => this.trigger('do-action', args));
        this.env.model.on('history-back', this, () => this.trigger('history-back'));
        
        // Umina edit: if 'barcode_open_line' is in context, instantly
        // open lines edit view
        if ('barcode_open_line' in this.props.action.context) {
            if (this.lines.length > 0) {
                this._openLineOnMount(this.lines[0])
            }
        }

    },

    async _openLineOnMount(line) {
        const virtualId = line.virtual_id;
        await this.env.model.save();
        // Updates the line id if it's missing, in order to open the line form view.
        if (!line.id && virtualId) {
            line = this.env.model.pageLines.find(l => Number(l.dummy_id) === virtualId);
        }
        this._editedLineParams = { currentId: line.id };
        await this.openProductPage();
    }
})