import logging

from odoo import fields, models
from odoo.addons.um_elgras.models.helpers_functions import StatusDetail, send_get_package_status, fill_package_data, \
    dpd_in_progress_delivery_statuses, get_config, check_token

_logger = logging.getLogger(__name__)


class DPDParcelStatus(models.Model):
    """ Add columns in 'WH/OUT' popup window """
    _inherit = 'stock.move.line'
    delivery_slip = fields.Binary(related='result_package_id.delivery_slip')
    manifest = fields.Binary(related='result_package_id.manifest')
    parcel_number = fields.Char(related='result_package_id.parcel_number', string="Package ID")
    package_number = fields.Char(related='result_package_id.package_number', string="Package Number")
    dpd_status = fields.Char(related='result_package_id.dpd_status')

    # Mode details card data

    dpd_tour = fields.Char(related='result_package_id.dpd_tour')
    dpd_coordinates = fields.Char(related='result_package_id.dpd_coordinates')
    dpd_delivery_estimate = fields.Char(related='result_package_id.dpd_delivery_estimate')
    dpd_depot = fields.Char(related='result_package_id.dpd_depot')
    dpd_country_code = fields.Char(related='result_package_id.dpd_country_code')

    dpd_country_name = fields.Char(related='result_package_id.dpd_country_name')
    dpd_city = fields.Char(related='result_package_id.dpd_city')

    # Metadata for handling packages
    dpd_state = fields.Selection(related='result_package_id.dpd_state')

    is_quotation_sent = fields.Boolean()

    def _cron_dpd_bearer_check(self):
        """
            Checks bearer token and updates it
        """
        url = get_config(self, "dpd.mainnet.api.url.base")
        bearer = get_config(self, "dpd.mainnet.bearer")
        check_token(self, url, bearer)

    def _cron_dpd_check(self):
        """
            Cron dpd daily check
        """
        # Get all stock elements is_courier_called_dpd
        # TODO: set finished delivery status to limit check count
        stock_piking = self.env['stock.picking'].search(
            [('is_courier_called_dpd', '!=', True) ])

        targeted_packages = []
        for line in stock_piking.move_line_ids:
            parcel_number = line.result_package_id.package_number
            parcel_status = line.result_package_id.dpd_status
            if parcel_number:
                # All packages that are sent to dpd, have ID
                # but still have no parce status
                if not parcel_status:
                    targeted_packages.append(line)
                # If parcel is processing
                if parcel_status in dpd_in_progress_delivery_statuses:
                    targeted_packages.append(line)
        # TODO: possible to improve code, reduce necessary packages
        targeted_packages_id_ = [x.package_number for x in targeted_packages]
        _logger.debug(f"Targeted ids: '{targeted_packages_id_}' packages...")
        targeted_packages_id = list(set(targeted_packages_id_))
        _logger.info(f"Targeted ids: '{targeted_packages_id}'  (SET) packages...")

        package_status = send_get_package_status(self, packages=targeted_packages_id,
                                                 bearer=get_config(self, "dpd.mainnet.bearer"),
                                                 detail=StatusDetail.ADVANCED, show_all=True)
        _logger.info("Running daly cron job")
        _logger.info(f"Checking '{len(package_status)}' packages...")

        fill_package_data(self, targeted_packages, package_status)


class DPDParcelStatusRel(models.Model):
    """ Add columns in 'WH/OUT' popup window """
    _inherit = 'stock.quant.package'

    delivery_slip = fields.Binary(string='Delivery Slip', help="DPD label")
    manifest = fields.Binary(string='Manifest')
    parcel_number = fields.Char(string='Parcel number', help="DPD delivery ID")
    package_number = fields.Char(string='DPD package number', help="Unique dpd package number for each sent package")
    dpd_status = fields.Char(string='DPD Status', help="DPD delivery Status")

    # Mode details card data

    dpd_tour = fields.Char(string='DPD Tour', help="DPD tour identifier")
    dpd_coordinates = fields.Char(string='DPD Coordinates',
                                  help="GPS Latitude/Longitude of the place where event was made.")
    dpd_delivery_estimate = fields.Char(string='DPD Estimate Delivery',
                                        help="Aproximate delivery time.")
    dpd_depot = fields.Char(string='DPD Depot',
                            help="DPD identifier of depot where scan was made.")
    dpd_country_code = fields.Char(string='DPD Country Code',
                                   help="ISO-3166 code of country where scan was made.\nExamples: 440, 428, 233")

    dpd_country_name = fields.Char(string='DPD Country Name',
                                   help="ISO-3166-2 name of country where scan was made.\nExamples: LT, LV, EE")
    dpd_city = fields.Char(string='DPD City',
                           help="City where DPD depot is located.")

    # Metadata for handling packages
    dpd_state = fields.Selection(
        [
            ('default', 'Default'),
            ('in_progress', 'In Progress'),
            ('sent', 'Sent'),
        ],
        string='Status',
        default='default',
        help="dpd delivery package states")

    is_quotation_sent = fields.Boolean(help="Is quotation sent")
