# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo.addons.bus.controllers.main import BusController


class MRPMPSController(BusController):

    # ---------------------------
    # Extends BUS Controller Poll
    # ---------------------------
    def _poll(self, dbname, channels, last, options):
        if request.session.uid:
            channels = list(channels)
            channels.append('mrp_mps_channel')
            channels.append('mrp_production')
            channels.append('mrp_workorder')
        return super()._poll(dbname, channels, last, options)
