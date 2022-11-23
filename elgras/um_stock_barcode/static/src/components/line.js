/** @odoo-module **/

import MainComponent from '@stock_barcode/components/main';
import { patch } from 'web.utils';
import { useService} from "@web/core/utils/hooks";




// Owl Render
const { Component, hooks } = owl;
const { useState, onWillStart, onMounted } = hooks;



patch(MainComponent.prototype, 'um_stock_barcode', {
    setup()
    {
        this.action = useService("action"); // for calling wizards
        this._super.apply(this, arguments);
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.userService = useService("user");
        onWillStart(async () => {
            this.data = await this.orm.call("stock.picking", "get_button_states", [[this.props.id]]);
            this.saveValue()
        });

        this.state = useState(
                        {
                            isPackageCreated: false,
                            isGenerateLabels: false,
                            isManifestGenerated: false,
                            isCourierCalled: false,

                                });

        console.log(this.state)
    },


    saveValue(){
        // Saves button states from stock.picking to this.state
        console.log("setting state")
        this.state.isPackageCreated = this.data.package
        this.state.isGenerateLabels = this.data.label
        this.state.isManifestGenerated = this.data.manifest
        this.state.isCourierCalled = this.data.courier
        this.state.isOrigin = this.data.origin
        this.state.isDPDTag = this.data.is_dpd_tag

        if (this.data.sequence == "PICK") {
            this.state.isSequencePICK = true;
            console.log( this.state.isSequencePICK = true)
        } else {
            this.state.isSequencePICK = false;
        }
        console.log("---props ")
        console.log(this.data)
        console.log(this.state)

    },

    async callOrmDownload(functionToCall)
    {
         let response = await this.orm.call("stock.picking", functionToCall, [[this.props.id]])
         console.log(response)
//         window.location.assign("http://localhost:8069/web/content/909?download=true");
         window.location.assign(response.url);
    },

//    Display wizard in barcode module
    async callOrmWizard(functionToCall)
    {
         let response = await this.orm.call("stock.picking", functionToCall, [[this.props.id]])
         console.log(response)
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Reciprocities',
            res_model: "mail.compose.message",
            views: [[false, 'form']],
            view_type: 'form',
            view_mode: 'tree',
            target: 'new',
            context: response.context,
        });


    },

    async callOrm(functionToCall) {
        console.log(`calling function ${functionToCall}`)
        let response = await this.orm.call("stock.picking", functionToCall, [[this.props.id]]);
        console.log(response)

        // Sends notification
        this.notification.add(this.env._t("Siunčiama užklausa"), {
            sticky: false,
            type: "info",
        });

        if (functionToCall == "action_delivery_send_package_to_dpd")
            {
                this.state.isPackageCreated = true;
            }
        if (functionToCall == "action_delivery_generate_manifest")
            {
                this.state.isManifestGenerated = true;
            }
        if (functionToCall == "action_delivery_download_delivery_slip")
            {
                this.state.isGenerateLabels = true;
            }
        if (functionToCall == "action_call_courier")
            {
                this.state.isCourierCalled = true;
            }

    },


});