# -*- coding: utf-8 -*-
import datetime
import json
import logging

from odoo import models, api, fields, _
from odoo.addons.um_elgras.models.helpers_functions import send_post_request, get_pick_pack_out_ids, DeliveryType, \
    get_config, update_bearer_token, get_next_day, \
    send_get_request, get_today, send_get_package_status, fill_package_data, StatusDetail, send_get_url_request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def is_production(self):
    conf = self.env["ir.config_parameter"]
    production = conf.sudo().get_param("dpd.is_production")
    if production:
        # Production
        bearer_token_key = "dpd.mainnet.bearer"
        url_base = "https://esiunta.dpd.lt/api/v1"
    else:
        bearer_token_key = "dpd.testnet.bearer"
        url_base = "https://sandbox-esiunta.dpd.lt/api/v1"
    return bearer_token_key, url_base


def get_delivery_slip_response(self, package_id):
    """
    Get all delivery labels from dpd based on packageid
    "offsetPosition":
        1 - top    left
        2 - bottom left
    :param package_id: package id from DPD
    :return: json response
    """
    data = {
        "shipmentIds": [package_id],
        "parcelNumbers": [],
        "offsetPosition": 0,
        "emailLabel": False,
        "downloadLabel": True,
        "pickupAddressVisibleOnLabel": True,
        # "labelFormat": "image/png",
        "labelFormat": "application/pdf",
        "paperSize": "A6"
    }
    endpoint = "/shipments/labels"
    bearer_token_key, url_base = is_production(self)
    base_endpoint = url_base + endpoint
    return send_post_request(url=base_endpoint, data=data, bearer_token=get_config(self, bearer_token_key))


def get_delivery_slip_response_individual(self, package_display_name):
    """
    Get individual labels from dpd based on parcel numbers
    "offsetPosition":
        1 - top    left
        2 - bottom left
    :param package_id: package id from DPD
    :return: json response
    """
    data = {
        "parcelNumbers": [package_display_name],
        "offsetPosition": 0,
        "emailLabel": False,
        "downloadLabel": True,
        "pickupAddressVisibleOnLabel": True,
        "labelFormat": "image/png",
        # "labelFormat": "application/pdf",
        "paperSize": "A6"
    }
    endpoint = "/shipments/labels"
    bearer_token_key, url_base = is_production(self)
    base_endpoint = url_base + endpoint
    return send_post_request(url=base_endpoint, data=data, bearer_token=get_config(self, bearer_token_key))


def get_manifest_response(self, package_id):
    """
    Get Manifest for DPD package
    :param self: odoo object
    :param package_id: package id from DPD
    :return:
    """
    data = {
        "shipmentIds": [package_id]
    }
    endpoint = "/shipments/manifests"
    bearer_token_key, url_base = is_production(self)
    base_endpoint = url_base + endpoint
    return send_post_request(url=base_endpoint, data=data, bearer_token=get_config(self, bearer_token_key))


class DPD(models.Model):
    _inherit = 'stock.picking'

    # button to filter button in picking section is_dpd_buttons_enabled
    enable_dpd_button = fields.Boolean(related="location_dest_id.is_dpd_buttons_enabled")
    is_send_package_to_dpd = fields.Boolean()
    is_manifest_generated_from_dpd = fields.Boolean()
    is_label_generated_from_dpd = fields.Boolean()
    is_courier_called_dpd = fields.Boolean()
    manifest_related = fields.Binary(related="move_line_ids.manifest")
    delivery_slip_related = fields.Binary(related="move_line_ids.delivery_slip")

    # tags
    is_dpd_tag = fields.Boolean('sale.order', compute="_get_sale_order_tags")
    tag_ids_related = fields.Many2many(related="sale_id.tag_ids", string="Sale Order Tags")

    def _get_sale_order_tags(self):
        """Get DPD tag  for stock.picking model"""
        self.ensure_one()
        quotation = self.env['sale.order'].search(
            [('state', '!=', 'cancel'), ('name', '=', self.origin)])
        for tag in quotation.tag_ids:
            if tag.name == "DPD":
                self.is_dpd_tag = True
                return
        self.is_dpd_tag = False

    def get_button_states(self):
        """
        Get button states for barcode module
        """
        package_created = self.is_send_package_to_dpd
        print(self.picking_type_id.sequence_code)
        label = self.is_label_generated_from_dpd
        manifest_generated = self.is_manifest_generated_from_dpd
        courier_called = self.is_courier_called_dpd
        sequence_code = self.picking_type_id.sequence_code
        return {"package": package_created, "label": label, "manifest": manifest_generated, "courier": courier_called,
                "origin": self.origin, 'sequence': sequence_code, 'is_dpd_tag': self.is_dpd_tag}

    @api.model
    def post_shipping(self):
        """
        Post basic shipment to dpd
            package_ids - weight visible only when packages are confirmed
        If Quotation in not validated, package weight need's to be recalculated
        :return DPD package ID
        """
        _logger.info(f"Handling {self.name}")
        _logger.info(f"Move type {self.move_type}")
        receiver_address, sender_address, service = self.get_receiver_data()
        package_count = len(self.package_ids)
        if not package_count:
            _logger.info(f"Package count: {package_count}")
            raise UserError(_('Nėra pakuočių siuntimui'))

        packages = []

        for package in self.package_ids:
            re_calculated_weight: float = 0  # This var is used when calling from barcode module
            _logger.info(f"Parsing package {package.display_name}")
            if package.weight > 31.5:
                raise UserError(_(f'General limit for packages: 31.5\nCurrent weight: {package.weight}'))
            if package.weight == 0:
                # Manually calculate package weight when running this function from barcode
                for pkg in package.move_line_ids:
                    re_calculated_weight += pkg.qty_done * pkg.product_id.weight
                    _logger.info(
                        f'QTY product_qty {pkg.product_qty}\nqty_done: {pkg.qty_done}\nproduct_uom_qty: {pkg.product_uom_qty}')
                    if re_calculated_weight == 0:
                        raise UserError(_(f'Neleistinas pakuotės dydis: {package.weight}'))
            _logger.info(f"Package weight calculated: {package.weight}")
            _logger.info(f"Package weight: {self.weight}")
            # Add sku code to package
            skus = package.move_line_ids.product_id.mapped("default_code") if package.move_line_ids else ""
            package_data = {
                "weight": package.weight if package.weight != 0 else re_calculated_weight,
                "mpsReferences": skus,
            }

            packages.append(package_data)
        package_data = {
            "parcels": packages
        }
        logging.debug(package_data)
        new_shipment = [{**sender_address, **receiver_address, **service, **package_data}]
        try:
            bearer_token_key, url_base = is_production(self)
            base_endpoint = url_base + "/shipments"
            response = send_post_request(data=new_shipment, url=base_endpoint,
                                         bearer_token=get_config(self, bearer_token_key))
            _logger.info(f"Request response code: {response.status_code}")

            if not response.ok:
                # Attempt to retrieve bearer token
                if "unauthorized" in response.text:
                    logging.warning("Bearer token is invalid updating bearer token")
                    update_bearer_token(self)

            if response.status_code == 201:
                _logger.info(f"Shipment successfully published!")
                response_json = response.json()

                dpd_package_id = response_json[0].get("id")
                print(dpd_package_id)
                _logger.debug(f'All products: {[x.result_package_id for x in self.move_line_ids]}')

                # Adds package ID not parcel number for tracking in QUOTATION
                for product in self.move_line_ids:
                    for package in self.package_ids:
                        if product.result_package_id.display_name == package.display_name:
                            product.result_package_id.parcel_number = dpd_package_id

                self.message_post(body=f"DPD: Siunta sukurta '{dpd_package_id}'")
                return dpd_package_id

            else:
                _logger.error(f"Failed to send request to dpd {response.status_code}")
                _logger.error(f"DPD response content: {response.content}")

                parsed = False
                try:
                    # Parse response content to get error message
                    error_message = json.loads(response.content.decode("utf-8"))
                    response_content_parsed = ""
                    for element in error_message:
                        response_content_parsed += element.get("title") + "\n"
                        parsed = True
                except Exception as e:
                    logging.warning(f"Failed to parse error content: {e}")

                raise UserError(
                    _(f'Klaida siunčiant užklausą į DPD.\n'
                      f'\tStatus Code: {response.status_code}\n'
                      f'\tReason: {response.reason}\n'
                      f'\tContent: {response_content_parsed if parsed else response.content}'))

        except Exception as e:
            _logger.error(f'Message: {e} {e.__traceback__}')
            if "Unauthorized" in e.__str__():
                self.message_post(body="Atnaujinami paramentrai, prašome pabandyti iš naujo")
                update_bearer_token(self)

            else:
                raise UserError(f'Nenumatyta klaida.\n\t{e}')

    def order_courier(self, parcerl_numbers):
        """
        Order currier to pick up packages
        Tries to orde courier today, tomorrow or next working day
        :param parcerl_numbers: posted package id
        :returns if true return request object else return False
        """
        _logger.info("DPD API requesting currier")
        # sender_company_name = self.company_id.partner_id.display_name
        # sender_sender_county_code = self.company_id.partner_id.country_code
        # sender_sender_company_email = self.company_id.partner_id.email
        # sender_mobile_phone = self.company_id.partner_id.phone_sanitized
        # sender_street = self.company_id.partner_id.street or self.company_id.partner_id.street2
        # sender_zip = self.company_id.partner_id.zip
        # sender_city = self.company_id.city
        sender_company_name = self.sale_id.warehouse_id.partner_id.display_name
        sender_sender_county_code = self.sale_id.warehouse_id.partner_id.country_code
        sender_sender_company_email = self.sale_id.warehouse_id.partner_id.email
        sender_mobile_phone = self.sale_id.warehouse_id.partner_id.phone_sanitized
        sender_street = self.sale_id.warehouse_id.partner_id.street or self.sale_id.warehouse_id.partner_id.street2
        sender_zip = self.sale_id.warehouse_id.partner_id.zip
        sender_city = self.sale_id.warehouse_id.partner_id.city

        # Try to order courier today
        day = get_today()
        response = self._order_courier(day, parcerl_numbers, sender_city, sender_company_name,
                                       sender_mobile_phone, sender_sender_company_email, sender_sender_county_code,
                                       sender_street, sender_zip)
        if response.status_code != 200:
            # Try to order courier tomorrow
            _logger.warning(f"Calling today failed, trying next day")
            day = get_next_day()
            response = self._order_courier(day, parcerl_numbers, sender_city, sender_company_name,
                                           sender_mobile_phone, sender_sender_company_email, sender_sender_county_code,
                                           sender_street, sender_zip)
        if response.status_code == 200:
            _logger.info(f"Courier pickup ordered! ")
            _logger.info(response.json())
            # self.message_post(body=f"DPD: Kurjeris iškviestas: '{day}'")
            return response.json()
        response_message = response.json().get("title")
        if response_message.startswith("Next working day"):
            # If wrong pickup date is entered order next working day, get value from DPD response
            next_working_day = response_message.split()[-1]
            _logger.info(f"Getting next working day {next_working_day}")
            response = self._order_courier(next_working_day, parcerl_numbers, sender_city,
                                           sender_company_name,
                                           sender_mobile_phone, sender_sender_company_email, sender_sender_county_code,
                                           sender_street, sender_zip)
            if response.status_code == 200:
                _logger.info(f"Courier pickup ordered! ")
                # self.message_post(body=f"DPD: Kurjeris iškviestas sekančią darbo dieną `{next_working_day}`")
                _logger.info(response.json())
                return response.json()

        else:
            raise UserError(f'Klaida siunčiant siuntą kurjeriui\nAr kurjeris jau iškviestas?\n{response.json()}')

    def _order_courier(self, pickup_date, parcerl_numbers, sender_city, sender_company_name,
                       sender_mobile_phone, sender_sender_company_email, sender_sender_county_code, sender_street,
                       sender_zip):

        conf = self.env["ir.config_parameter"]
        pick_up_from = conf.sudo().get_param("dpd.pickup_time_from")
        pick_up_to = conf.sudo().get_param("dpd.pickup_time_to")

        pickup_time_from_dpd = pick_up_from if pick_up_from else "12:00"
        pickup_time_to_dpd = pick_up_to if pick_up_to else "17:00"

        sender_address = {
            "messageToCourier": "a_",
            "pickupDate": pickup_date,
            "pickupTimeFrom": pickup_time_from_dpd,
            "pickupTimeTo": pickup_time_to_dpd,
            "shipmentIds": [parcerl_numbers],
            "address": {
                "name": sender_company_name,
                "contactName": sender_company_name,
                "contactInfo": sender_street,
                "email": sender_sender_company_email,
                "phone": sender_mobile_phone,
                "street": sender_street,
                "city": sender_city,
                "postalCode": sender_zip,
                "country": sender_sender_county_code
            }

        }
        # Parcel count that must be picked up
        # Each parcel must not exceed 31.5 kg. If a parcel is heavier than 31.5 kg, it must be submitted as a pallet.
        total_weight1 = self.shipping_weight
        total_weight2 = self.weight
        if total_weight1 == 0 and total_weight2 == 0:
            raise UserError("Neteisingas siuntinio bendras dydis: 0")
        print(f"self.shipping_weight: {total_weight1}")
        print(f"self.weight: {total_weight2}")
        if self.shipping_weight != 0:
            packages = {
                "parcel": {
                    "count": len(self.package_ids),
                    "weight": total_weight1
                }}
        else:
            packages = {
                "parcel": {
                    "count": len(self.package_ids),
                    "weight": total_weight2
                }}

        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        pickups_data = {**sender_address, **packages}
        bearer_token_key, url_base = is_production(self)
        base_endpoint = url_base + "/pickups"
        response = send_post_request(data=pickups_data, url=base_endpoint, headers=headers,
                                     bearer_token=get_config(self, bearer_token_key))
        if response.status_code != 200:
            logging.warning(f"Calling courier failed: {pickup_date}")
            logging.warning(f"Calling call info:\n{sender_address}\n{packages}")
            logging.warning(f"Response data:: {response.json()}")
        if response.status_code == 200:
            self.message_post(
                body=f"DPD: Kurjeris iškviestas: '{pickup_date}' nuo: {pickup_time_from_dpd} iki {pickup_time_to_dpd}.")
        return response

    def get_package_numbers_request(self, package_id):
        """
        Gets parcel number created after manifest based of package_id
        dpd_delivery_id example: '5bd206ff-8201-4781-a894-a37f824a6633'
        """
        endpoint = "/shipments"
        params = {'ids[]': package_id}
        bearer_token_key, url_base = is_production(self)
        base_endpoint = url_base + endpoint
        return send_get_request(url=base_endpoint, params=params, bearer_token=get_config(self, bearer_token_key))

    def get_manifest(self, dpd_package_id):
        """
        Get manifest data from dpd API
        :param dpd_package_id: unique identifier for dpd package
        :return:
        """
        try:
            dpd_manifest_ = get_manifest_response(self, dpd_package_id)
            if dpd_manifest_.status_code == 200:
                dpd_manifest = dpd_manifest_.json()
                dpd_manifest_id = dpd_manifest.get("shipmentIds")[0]
                dpd_manifest_data = dpd_manifest.get('binaryData').split(",")[1]
                for product in self.move_line_ids:
                    if product.result_package_id.parcel_number == dpd_manifest_id:
                        product.result_package_id.manifest = dpd_manifest_data

                self.message_post(body=f"DPD: Manifestas uždarytas.")
                return dpd_manifest.get("parcelNumbers")
            else:
                raise UserError(
                    _(f'Klaida gaunant siuntos manifestą.\n'
                      f'\tStatus Code: {dpd_manifest_.status_code}\n'
                      f'\tReason: {dpd_manifest_.reason}\n'
                      f'\tContent: {dpd_manifest_.content}'))

        except Exception as e:
            _logger.error(f'Message: {e} {e.__traceback__}')

    def get_delivery_slip_individual(self, parcel_numbers_ids):
        """
        Get delivery slip data from dpd API
        This delivery slip gets individual slips based on package
        :param parcel_numbers_ids numbers from generated manifest or after generated delivery slip
        """
        try:
            for parcel_id in parcel_numbers_ids:
                print(f"processing {parcel_id}")
                dpd_label_ = get_delivery_slip_response_individual(self, parcel_id)
                if dpd_label_.status_code == 200:
                    _logger.info(f"Request successfully created!")
                    dpd_label = dpd_label_.json()
                    for product in self.move_line_ids[::-1]:
                        if product.result_package_id.package_number == parcel_id:
                            product.result_package_id.delivery_slip = \
                                dpd_label.get("pages")[0]['binaryData'].split(",")[1]
                            # Message in chatter
                            self.message_post(body=f"DPD: Etiketė siuntai {parcel_id}  atspausdinta.")
        except Exception as e:
            _logger.error(f'Message: {e} {e.__traceback__}')
            raise UserError(
                (f'Klaida gaunant delivery Slips.\n'
                 f'\tStatus Code: {dpd_label_.status_code}\n'
                 f'\tReason: {dpd_label_.reason}\n'
                 f'\tContent: {dpd_label_.content}'))

    def get_delivery_slip(self, dpd_package_id):
        """
        Get delivery slip data from dpd API
            This delivery slip gets all slips based on package
        :param dpd_package_id: unique identifier for dpd package
        :return package numbers
        """
        try:
            dpd_label_ = get_delivery_slip_response(self, dpd_package_id)
            if dpd_label_.status_code == 200:
                _logger.info(f"Request successfully created!")
                dpd_label = dpd_label_.json()
                dpd_label_id = dpd_label.get("shipmentIds")[0]

                picture_data = dpd_label.get("pages")[0]['binaryData'].split(",")[1]
                # With packages, get all slips at once
                # picture_cropped = crop_picture(picture_data)
                for product in self.move_line_ids:
                    if product.parcel_number == dpd_label_id:
                        product.result_package_id.delivery_slip = picture_data
                        # Message in chatter
                        self.message_post(body=f"DPD: Etiketė atspausdinta.")
                return dpd_label.get('parcelNumbers')
            else:
                raise UserError(
                    _(f'Klaida gaunant delivery Slips.\n'
                      f'\tStatus Code: {dpd_label_.status_code}\n'
                      f'\tReason: {dpd_label_.reason}\n'
                      f'\tContent: {dpd_label_.content}'))
        except Exception as e:
            _logger.error(f'Message: {e} {e.__traceback__}')

    def get_receiver_data(self):
        """For shipping form for dpd request to /shipments
        DPD Classic - (B2B) service
            DPD to-door delivery
        Classic (ES) - DPD CLassic (ES) paslaugos apimtyje palečių -
        """
        receiver_m = self.partner_id.name
        if not receiver_m:
            raise UserError("Please enter receiver name")
        if len(receiver_m) > 35:
            raise UserError(
                "Receiver name is too long. Max 35 characters.\n Current length: {}".format(len(receiver_m)))

        receiver_city_m = self.partner_id.city
        if not receiver_city_m:
            raise UserError("Please enter receiver city")
        if len(receiver_city_m) > 35:
            raise UserError(
                "Receiver city is too long. Max 35 characters.\n Current length: {}".format(len(receiver_city_m)))

        receiver_street_m = self.partner_id.street or self.partner_id.street2
        if not receiver_street_m:
            raise UserError(
                "Please enter receiver street \n"
                "In case it is not possible to separate, this can contain property number + flat number.")
        if len(receiver_street_m) > 35:
            raise UserError(
                "Receiver street is too long. Max 35 characters.\n Current length: {}".format(len(receiver_street_m)))

        receiver_phone_m = self.partner_id.phone_sanitized
        if not receiver_phone_m:
            raise UserError("Please enter receiver phone")
        if len(receiver_phone_m) > 30:
            raise UserError(
                "Receiver phone is too long. Max 30 characters.\n Current length: {}".format(len(receiver_phone_m)))

        receiver_zip = self.partner_id.zip
        if not receiver_zip:
            raise UserError("Please enter receiver zip\nWithout the country code and spaces.")
        if len(receiver_zip) > 7:
            raise UserError(
                "Receiver zip is too long. Max 7 characters.\n Current length: {}".format(len(receiver_zip)))

        receiver_county_code_m = self.partner_id.country_code
        if not receiver_county_code_m:
            raise UserError(
                "Please enter receiver country code\nISO 3166-1 alpha-2 country codes format, e.g. LT, LV, EE.")
        if len(receiver_county_code_m) > 3:
            raise UserError("Receiver country is too long. Max 3 characters.\n Current length: {}".format(
                len(receiver_county_code_m)))

        receiver_email_o = self.partner_id.email

        package_count = len(self.package_ids) or 1
        _logger.info(f"Package count: {package_count}")

        sender_address = self.get_sender_data()
        receiver_address = {
            "receiverAddress": {
                "name": receiver_m,
                "email": receiver_email_o,
                "phone": receiver_phone_m,
                "street": receiver_street_m,
                "city": receiver_city_m,
                "postalCode": receiver_zip,
                "country": receiver_county_code_m
            }}
        if receiver_county_code_m in "LT,LV,EE,PL,FIN".split(","):
            service = {
                "service": {
                    "serviceAlias": "DPD Classic"
                }}
        else:
            service = {
                "service": {
                    "serviceAlias": "Classic (ES)"
                }}

        return receiver_address, sender_address, service

    def get_sender_data(self):
        """
            Get sender data and validate required inputs
        """
        # Fix start: display warehouse address, override default company as sender
        sender_warehouse = self.sale_id.warehouse_id
        sender_warehouse.ensure_one()

        company_id = sender_warehouse.partner_id

        sender_company_name_m = company_id.display_name
        if not sender_company_name_m:
            raise UserError("Please enter sender company name")
        if len(sender_company_name_m) > 35:
            raise UserError(
                "Sender name is too long. Max 35 characters.\n Current length: {}".format(len(sender_company_name_m)))

        sender_sender_county_code_m = company_id.country_code
        if not sender_sender_county_code_m:
            raise UserError(
                "Please enter sender country code\nISO 3166-1 alpha-2 country codes format, e.g. LT, LV, EE.")
        if len(sender_sender_county_code_m) > 3:
            raise UserError("Sender country is too long. Max 3 characters.\n Current length: {}".format(
                len(sender_sender_county_code_m)))

        sender_mobile_phone_m = company_id.phone_sanitized
        if not sender_mobile_phone_m:
            raise UserError("Please enter sender mobile phone\n"
                            "Only one phone number on this parameter. No other information should be provided here!\n"
                            "There must be an international country code provided. e.g. “+372555555”, “+37065123456\n"
                            "If there is no country code, it will be added automatically based on the country parameter.")
        if len(sender_mobile_phone_m) > 30:
            raise UserError(
                "Sender phone is too long. Max 30 characters.\n Current length: {}".format(len(sender_mobile_phone_m)))

        sender_street_m = company_id.street or company_id.street2
        if not sender_street_m:
            raise UserError("Please enter sender street\n"
                            "In case it is not possible to separate, this can contain street name + property number or street name + property number + flat number")
        if len(sender_street_m) > 35:
            raise UserError(
                "Sender street is too long. Max 35 characters.\n Current length: {}".format(len(sender_street_m)))

        sender_zip_m = company_id.zip
        if not sender_zip_m:
            raise UserError("Please enter sender zip")
        if len(sender_zip_m) > 7:
            raise UserError(
                "Sender zip is too long. Max 7 characters.\n Current length: {}".format(len(sender_zip_m)))

        sender_city_m = company_id.city
        if not sender_city_m:
            raise UserError("Please enter sender city")
        if len(sender_city_m) > 35:
            raise UserError(
                "Sender city is too long. Max 35 characters.\n Current length: {}".format(len(sender_city_m)))

        sender_sender_company_email_o = company_id.email
        sender_address = {
            "senderAddress": {
                "name": sender_company_name_m,
                "email": sender_sender_company_email_o,
                "phone": sender_mobile_phone_m,
                "street": sender_street_m,
                "city": sender_city_m,
                "postalCode": sender_zip_m,
                "country": sender_sender_county_code_m
            }}
        return sender_address

    def action_delivery_send_package_to_dpd(self):
        """Creates DPD package"""
        dpd_package_id = self.post_shipping()
        if dpd_package_id:
            self.is_send_package_to_dpd = True

    def action_delivery_generate_manifest(self):
        """Get manifest from DPD API"""

        try:
            # All packages have same parcel_number, lets pick first one
            dpd_delivery_id = self.package_ids[0].parcel_number
            if not dpd_delivery_id:
                raise UserError("Trūksta siuntos ID.")
            logging.info(f"Getting manifest for parcel: '{dpd_delivery_id}'")
            parcel_numbers = self.get_manifest(dpd_delivery_id)
            logging.info(f"Parcel numbers from manifest: '{parcel_numbers}'")
            if parcel_numbers:
                self.is_manifest_generated_from_dpd = True
            self.set_package_numbers_from_dpd(dpd_delivery_id)
        except IndexError as e:
            logging.warning(f'Trūksta siuntos ID\n{e}')
            raise UserError(f'Trūksta siuntos ID\nPrašome sukurti siuntą')
        except Exception as e:
            raise UserError(f'Nenumatyta klaida.\n\t{e}')

    def action_delivery_download_manifest(self):
        # TODO: probably there is better and direct way of doing this
        today = datetime.datetime.now()
        date_time = today.strftime("-%Y-%d-%m-%H-%M-%S")
        name_of_file = f'Manifest{date_time}.pdf'
        result_id = self.env['export.product'].create({'file': self.manifest_related, 'file_name': name_of_file})
        return {
            'name': 'Manifest',
            'view_mode': 'form',
            'res_id': result_id.id,
            'res_model': 'export.product',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def set_package_numbers_from_dpd(self, dpd_delivery_id):
        """
        Gets package numbers and refs after manifest is created
            and fills data in quant.package
        :param dpd_delivery_id: delivery package ID
        """
        try:
            packages_numbers_dpd_response = self.get_package_numbers_request(dpd_delivery_id)
            if packages_numbers_dpd_response.status_code == 200:
                packages_numbers = packages_numbers_dpd_response.json()
                if not packages_numbers.get("items"):
                    raise UserError(f'Netasti siuntiniai\n{packages_numbers}')
                packages_dpd_response = packages_numbers.get("items")[0].get("parcels")
                if len(self.move_line_ids) == len(packages_dpd_response):
                    for product, package_id in zip(self.move_line_ids, packages_dpd_response):
                        product.result_package_id.package_number = package_id.get("parcelNumber")
        except Exception as e:
            logging.error(f"Not essential error getting package numbers after generating manifest\n{e}")

    def action_delivery_download_delivery_slip(self):
        """
        Get delivery slip from DPD API  and call courier using DPD API
            To get each package slip 'parcel_numbers' is required
            parcel number is retrieved from 'manifest'
        """
        try:
            dpd_delivery_id = self.package_ids[0].parcel_number
            if not dpd_delivery_id:
                raise UserError("Trūksta siuntos ID.")
            package_numbers = self.get_delivery_slip(dpd_delivery_id)
            self.set_package_numbers_from_dpd(dpd_delivery_id)
            # self.get_delivery_slip_individual(parcel_numbers_ids=package_numbers)
            self.is_label_generated_from_dpd = True

        except IndexError as e:
            logging.warning(f'Trūksta siuntos ID \e {e}')
            raise UserError(f'Trūksta siuntos ID\nPrašome sukurti siuntą')
        except Exception as e:
            raise UserError(f'Nenumatyta klaida.\n\t{e}')

    def empty(self):
        "Retuns empty string"
        return ""

    def action_call_courier(self):
        """
        Action to call courier
        :return:
        """
        try:
            dpd_delivery_id = self.package_ids[0].parcel_number
            if not dpd_delivery_id:
                raise UserError("Trūksta siuntos ID.")
            response_courier = self.order_courier(dpd_delivery_id)

            if response_courier:
                self.is_courier_called_dpd = True

        except IndexError as e:
            logging.warning(f'Trūksta siuntos ID \e {e}')
            raise UserError(f'Trūksta siuntos ID\nPrašome sukurti siuntą')
        except Exception as e:
            raise UserError(f'Nenumatyta klaida.\n\t{e}')

    def action_download_attachment_manifest(self):
        """Downloads delivery slip as directly to browser"""
        return self._action_download_attachment('manifest')

    def action_download_attachment_slip(self):
        """Download manifest slip as directly to browser"""
        return self._action_download_attachment('delivery_slip')

    def action_call_report_attachment_slip(self):
        """
        Call report to download delivery slips
        """
        return {
            'type': 'ir.actions.report',
            'report_name': 'um_elgras.report_deliveryslip_dpd_view',
            'model': 'stock.picking',
            'report_type': "qweb-pdf",
        }

    def _action_download_attachment(self, file_to_download):
        """
        Get full url link to a download
        :param file_to_download: 'delivery_slip', 'manifest'
        :return: url
        """
        # TODO: change package id if you want to download individual package data
        # Assumption that all packages gave merged delivery slip
        package_id = self.package_ids[0].id

        attachment = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'stock.quant.package'),
            ('res_field', '=', file_to_download),
            ('res_id', '=', package_id),
        ], limit=1)

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        download_url = '/web/content/' + str(attachment.id) + '?download=true'
        print("action_delivery_generate_delivery_slip_qweb")
        if not attachment and not attachment.datas:
            raise UserError("No delivery slip to download")
        if attachment:
            # Fix so that all users can download files
            attachment.public = True
        print(str(base_url) + str(download_url))
        return {
            'name': 'Report',
            'type': 'ir.actions.act_url',
            'url': str(base_url) + str(download_url),
            'target': 'new',
        }

    def action_generate_dpd(self):
        """
        Generates dpd data
            Executed when send to DPD button is pressed
        """

        dpd_package_id = self.post_shipping()
        parcel_numbers = self.get_manifest(dpd_package_id)
        self.get_delivery_slip_individual(parcel_numbers)
        response_courier = self.order_courier(dpd_package_id)

        # set done quantities
        pack_delivery_object = get_pick_pack_out_ids(self, DeliveryType.PACK)
        out_delivery_object = get_pick_pack_out_ids(self, DeliveryType.OUT)
        pack_delivery_object.action_set_quantities_to_reservation()
        out_delivery_object.action_set_quantities_to_reservation()

    def action_send_confirmation_warehouse(self):
        """Sends carrier data"""
        self.ensure_one()
        quotation = self.env['sale.order'].search(
            [('state', '!=', 'cancel'), ('name', '=', self.origin)])

        template_id = self.env.ref('um_elgras.elgras_mail_template_from_warehouse').id
        lang = quotation.env.context.get('lang')
        template = quotation.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(quotation.ids)[quotation.id]
        ctx = {
            'default_model': 'sale.order',
            'default_res_id': quotation.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'proforma': quotation.env.context.get('proforma', False),
            'force_email': True,
            'model_description': quotation.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def action_send_carrier(self):
        """Sends carrier data"""
        self.ensure_one()
        quotation = self.env['sale.order'].search(
            [('state', '!=', 'cancel'), ('name', '=', self.origin)])

        template_id = self.env.ref('um_elgras.elgras_send_to_carrier_template').id
        lang = quotation.env.context.get('lang')
        template = quotation.env['mail.template'].browse(template_id)
        if template.lang:
            lang = template._render_lang(quotation.ids)[quotation.id]
        ctx = {
            'default_model': 'sale.order',
            'default_res_id': quotation.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'proforma': quotation.env.context.get('proforma', False),
            'force_email': True,
            'model_description': quotation.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }


class DPDParcelStatus(models.Model):
    """Show parcel status in Quotations'"""
    _inherit = "sale.order"
    move_line_ids = fields.Many2many('stock.move.line', compute='_compute_move_lines')

    def _compute_move_lines(self):
        """Fill Order Line Notebook field"""
        for order in self:
            move_lines = []
            order_picking_ids = order.picking_ids
            print(order_picking_ids)

            packages_and_items = {}
            # Set uniques packages only once, to display in Quotations "Siuntu Statusai"
            for product in order_picking_ids.move_line_ids:
                package = product.result_package_id.display_name
                packages_and_items[package] = product
            move_lines += [x.id for x in packages_and_items.values()]

            order.move_line_ids = [(6, 0, move_lines)]


    # def debug_set_package(self):
    #     print('haha')

    def update_dpd_package_status(self):
        """Triggered by 'Update DPD Statuses
            # parcel_number = '0172a5d2-d5b7-4949-9543-6197a76e53a9'
            # package_number = "05818022513131"
        '"""
        for package in self.move_line_ids:
            parcel_number = package.parcel_number
            package_number = package.package_number
            self.set_missing_package_number(package_number, parcel_number)
            self.get_package_status(package_number)

    def get_package_status(self, package_number):
        """
        # If there is package_number, check for package status
        # package numer is used to check parcel status
        """
        if package_number and package_number != "nerasta":
            bearer_token_prod = get_config(self, "dpd.mainnet.bearer")
            package_status = send_get_package_status(self, packages=[package_number], bearer=bearer_token_prod,
                                                     detail=StatusDetail.ADVANCED, show_all=True)
            fill_package_data(self, self.move_line_ids, package_status)

    def set_missing_package_number(self, package_number, parcel_number):
        """
        # if there is parcel_number, but there is no package_number then try to fetch package number
        """
        if parcel_number and not package_number or package_number == "nerasta":
            self.set_package_numbers_from_dpd(parcel_number)

    def set_package_numbers_from_dpd(self, dpd_delivery_id):
        """
        Gets package numbers and refs after manifest is created
            and fills data in quant.package
        :param dpd_delivery_id: delivery package ID
        """
        try:
            packages_numbers_dpd_response = self.get_package_numbers_from_id(dpd_delivery_id)
            if packages_numbers_dpd_response.status_code == 200:
                packages_numbers = packages_numbers_dpd_response.json()
                if not packages_numbers.get('parcelNumbers'):
                    return
                packages_dpd_response = packages_numbers.get("parcelNumbers")
                if len(self.move_line_ids) == len(packages_dpd_response):
                    for product, package_id in zip(self.move_line_ids, packages_dpd_response):
                        product.result_package_id.package_number = package_id
        except Exception as e:
            logging.error(f"Not essential error after checking package number\n{e}")

    def get_package_numbers_from_id(self, package_id):
        """
        Gets parcel number created after manifest based of package_id
        dpd_delivery_id example: '5bd206ff-8201-4781-a894-a37f824a6633'
        """
        endpoint = f"/shipments/{package_id}/manifests"
        bearer_token_key, url_base = is_production(self)
        base_endpoint = url_base + endpoint
        return send_get_url_request(url=base_endpoint, bearer_token=get_config(self, bearer_token_key))


class DPDOperationTypeExtend(models.Model):
    """DPD checkbox in operation types'"""
    _inherit = "stock.location"
    is_dpd_buttons_enabled = fields.Boolean(help="Button to display DPD buttons", default=False)
