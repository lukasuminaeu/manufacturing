odoo.define('um_mrp_user_workcenter/static/js/kanban_view.js', function (require) {
    "use strict";
    
var KanbanView = require('web.KanbanView');
var viewRegistry = require('web.view_registry');

var KanbanViewWithoutControlPanel = KanbanView.extend({
    // determines if a control panel should be instantiated
    withControlPanel: false,
    // determines if a search panel could be instantiated
    withSearchPanel: false,
})

viewRegistry.add('kanban_without_control_panel', KanbanViewWithoutControlPanel);

})