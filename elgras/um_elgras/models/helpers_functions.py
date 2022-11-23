import base64
import json
import logging
from datetime import datetime
from datetime import timedelta
from enum import Enum
from io import BytesIO

import requests
from PIL import Image
from requests.auth import HTTPBasicAuth

_logger = logging.getLogger(__name__)

dpd_done_delivery_statuses = ["Pristatyta gavėjui", "Pristatyta į siuntų tašką/terminalą",
                              "Gavėjas atsiėmė siuntą iš siuntų taško/terminalo",
                              "Delivered to Consignee",
                              "Delivered to Pickup Point" "Picked up by Consignee from Pickup point"
                              ]
dpd_in_progress_delivery_statuses = ["Atnešta į siuntų tašką/terminalą", "Kurjeris paėmė siuntą", "Pakeliui",
                                     "Dropped in Pickup Point", "Picked up by Courier", "En route"]


class PackageStatus:
    package_id: str
    status: str
    error: str

    def __str__(self):
        return f'PackageStatus(package_id={str(self.package_id)} '

    def __repr__(self):
        return f'PackageStatus(package_id={str(self.package_id)} '


class StatusDetail(Enum):
    BASIC = 0
    ADVANCED = 3


class DeliveryType(Enum):
    """Enum for delivery type"""
    PICK = "PICK"
    PACK = "PACK"
    OUT = "OUT"


def display_popup_message(title="klaida", message="message", sticky=False, display_type="info"):
    """
    :param title: title of your warning
    :param message: message of your warning
    :param sticky: if message is displayed as a sticky
    :param display_type:  success,warning,danger,info
    """
    title = title
    message = message
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': title,
            'message': message,
            'sticky': sticky,
            'type': display_type,

        }
    }


def get_next_day():
    """
    :return: next day str isoformat
    """
    next_day = datetime.now() + timedelta(days=1)
    return next_day.date().isoformat()


def get_today():
    """
    :return: get today
    """
    next_day = datetime.now()
    return next_day.date().isoformat()


def get_bearer_token(url_base, auth):
    """
    Receive bearer token for further authentication
    :return: bearer token
    """

    payload = {
        "name": "Unima 2022-04-25",
        "ttl": 99999999999
    }
    r = requests.post(url_base + "/auth/tokens",
                      auth=auth,
                      headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                      data=json.dumps(payload)
                      )
    if r.status_code == 200:
        print("Request ok")
        response = json.loads(r.text)
        print(response)
        bearer = response.get("token")
        return bearer
    else:
        print("Bad request")
        print(r.text)
        return ""


def crop_picture(picture_data, left=0, top=0, right=1210, bottom=1750, out_format="PNG"):
    """
    Crops image data
    :param picture_data: base64 png data
    :param bottom: rop dimensions
    :param right: crop dimensions
    :param top: crop dimensions
    :param left:  crop dimensions
    :param out_format: output format
    :return: cropped picture binary data
    """
    _logger.info("Cropping image")
    img = Image.open(BytesIO(base64.b64decode(picture_data)))

    img_res = img.crop((left, top, right, bottom))
    # img_res.show() # Show picture for debugging purposes
    output = BytesIO()
    img_res.save(output, format=out_format)
    data = output.getvalue()
    encoded = base64.b64encode(data)
    return encoded


def get_pick_pack_out_ids(self_object, name: DeliveryType):
    """
    Get quotation to retrieve all picking/packing/out
    :param self_object: self odoo object
    :param name: Name to filter PIC/PAC/OUT
    :return: pick/pack/out line ids
    """
    quotation = self_object.env['sale.order'].search(
        [('state', '!=', 'cancel'), ('name', '=', self_object.origin)])
    for pick_pack_out in quotation.picking_ids:
        if name.value in pick_pack_out.name:
            return pick_pack_out


def send_get_package_status(self, bearer: str, packages: list, language="lt", detail=StatusDetail.BASIC,
                            show_all=False):
    """
    Sends generic POST request
    :param bearer: bearer access token
    :param packages: pknr accepted multiple package format: '05818022512763|05818022512746'
    :param language: language to display information
    :param detail: return number of details / BASIC/ ADVANCED
    :param show_all: Display mode detailed information
    :return: Returns list of package status:
    Both are ok responses:
    detail=0 response:
        # [{'parcelNumber': '05818022512763', 'details': [{'status': 'Pakeliui', 'dateTime': '2022-04-14 13:47:51'}], 'error': None}, [...]}
        # [{'parcelNumber': '058180225127x', 'details': [], 'error': {'code': 400, 'message': 'Invalid parcel number...'}}]
    detail=3 response:
            {'serviceCode': '327', 'statusCode': '10', 'prevStatusCode': '05', 'dateTime': '2022-04-14 13:47:51',
            'Tour': '9', 'GpsLat': '', 'GpsLon': '', 'TimeFrame': '', 'AddCode': '095', 'Weight': '', 'Depot': '0076',
            'City': 'Strykow (PL)', 'CountryCode': '616', 'CountryIsoName': 'PL'}

    """

    url = "https://status.dpd.lt/external/tracking"
    _logger.info(f'Sending request to: {url}')

    list_of_packages = ""
    for package in packages:
        if package == packages[-1]:
            list_of_packages += package
            continue
        list_of_packages += package + "|"

    params = {'pknr': list_of_packages, 'lang': language, 'detail': str(detail.value),
              'show_all': '1' if show_all else '0'}
    headers = {'Accept': 'application/json'}
    header_bearer = {'Authorization': "Bearer " + bearer}
    headers.update(header_bearer)

    response = requests.get(url,
                            headers=headers,
                            params=params
                            )
    list_of_package_status = []

    if response.ok:
        _logger.info(f"Request ok! : {response.status_code}")
        packages = response.json()
        for package in packages:
            # Basic details
            if detail == StatusDetail.BASIC:
                pk_obj = PackageStatus()
                pk_obj.package_id = package.get("parcelNumber")
                if package.get("error"):
                    check_bearer_token(self, pk_obj)
                    pk_obj.error = package.get("error").get('message')
                if package.get("details"):
                    pk_obj.status = package.get("details")[0].get("status")
                list_of_package_status.append(pk_obj)

            # Advanced details with show all settings
            if show_all and detail == StatusDetail.ADVANCED:
                pk_obj = PackageStatus()
                pk_obj.package_id = package.get("parcelNumber")
                if package.get("error"):
                    pk_obj.error = package.get("error").get('message')
                    check_bearer_token(self, pk_obj)
                if package.get("details"):
                    pk_obj.status_obj = send_get_package_status(self, packages=[package.get("parcelNumber")],
                                                                bearer=bearer,
                                                                detail=StatusDetail.BASIC)
                    pk_obj.status = pk_obj.status_obj[0].status
                    pk_obj.status_pickup_date = package.get("details")[0].get("dateTime")

                    # Event date and time (YYYY-MM-DD HH:mm:ss)
                    pk_obj.date_time = package.get("details")[-1].get("dateTime")
                    pk_obj.tour = package.get("details")[-1].get("Tour")
                    pk_obj.gps_lat = package.get("details")[-1].get("GpsLat")
                    pk_obj.gps_long = package.get("details")[-1].get("GpsLon")
                    # Approximate delivery time (HHmm-HHmm)
                    pk_obj.delivery_date = package.get("details")[-1].get("TimeFrame")
                    pk_obj.status_code = package.get("details")[-1].get("statusCode")

                    # DPD identifier of depot where scan was made.
                    pk_obj.warehouse_code = package.get("details")[-1].get("Depot")
                    # ISO-3166 code of country where scan was made.
                    # Examples: 440, 428, 233
                    pk_obj.country_code = package.get("details")[-1].get("CountryCode")
                    # ISO-3166-2 name of country where scan was made.
                    # Examples: LT, LV, EE
                    pk_obj.country_iso_name = package.get("details")[-1].get("CountryIsoName")
                    # City where DPD depot is located.
                    pk_obj.country_name = package.get("details")[-1].get("City")

                list_of_package_status.append(pk_obj)
            # Advanced details
            if not show_all and detail == StatusDetail.ADVANCED:
                pk_obj = PackageStatus()
                pk_obj.package_id = package.get("parcelNumber")
                if package.get("error"):
                    pk_obj.error = package.get("error").get('message')
                    check_bearer_token(self, pk_obj)
                if package.get("details"):
                    pk_obj.status_obj = send_get_package_status(self, packages=[package.get("parcelNumber")],
                                                                bearer=bearer,
                                                                detail=StatusDetail.BASIC)
                    pk_obj.status = pk_obj.status_obj[0].status
                    pk_obj.date_time = package.get("details")[0].get("dateTime")
                    pk_obj.tour = package.get("details")[0].get("Tour")
                    pk_obj.gps_lat = package.get("details")[0].get("GpsLat")
                    pk_obj.gps_long = package.get("details")[0].get("GpsLon")
                    # Estimated delivery time
                    pk_obj.delivery_date = package.get("details")[0].get("TimeFrame")

                    pk_obj.status_code = package.get("details")[0].get("statusCode")

                list_of_package_status.append(pk_obj)

        return list_of_package_status
    else:
        _logger.error(f"Failed to send request {response.status_code}")
        return False


def get_config(self, parameter):
    """Get mainnet bearer token for parcel checking"""
    conf = self.env["ir.config_parameter"]
    bearer_token_prod = conf.sudo().get_param(parameter)
    if not bearer_token_prod:
        update_bearer_token(self)
        bearer_token_prod = conf.sudo().get_param(parameter)
    return bearer_token_prod


def check_bearer_token(self, pk_obj):
    """
    Check bearer token in package status check
    :param self: odoo self object
    :param pk_obj: Package object
    :return:
    """

    if pk_obj.error == "These credentials do not match our records!":
        logging.error("Invalid Bearer Token")
        logging.info("Atnaujinami paramentrai, prašome pabandyti iš naujo")
        update_bearer_token(self)


def check_token(self, base_url, bearer):
    """Checks whether bearer token is valid and updates it"""
    url = base_url + "/auth/me"
    bearer = {'Authorization': "Bearer " + bearer}
    r = requests.get(url, headers=bearer)
    if r.status_code != 200:
        _logger.info("Updating bearer tokens")
        update_bearer_token(self)
    else:
        # TODO: change status to debug
        _logger.info("Bearer token OK...")


def update_bearer_token(self):
    """Updates bearer tokens"""
    # TODO: disable testnet in production
    conf = self.env["ir.config_parameter"]
    bearer_api_mainnet_url = conf.sudo().get_param("dpd.mainnet.api.url.base")
    bearer_api_testnet_url = conf.sudo().get_param("dpd.testnet.api.url.base")

    #: TODO check bearer token
    bearer_token_mainnet = conf.sudo().get_param("dpd.mainnet.bearer")
    bearer_token_testnet = conf.sudo().get_param("dpd.testnet.bearer")
    mainnet_user = conf.sudo().get_param("dpd.mainnet.api.username")
    mainnet_pass = conf.sudo().get_param("dpd.mainnet.api.password")
    testnet_user = conf.sudo().get_param("dpd.testnet.api.username")
    testnet_pass = conf.sudo().get_param("dpd.testnet.api.password")
    basic_prod = HTTPBasicAuth(mainnet_user, mainnet_pass)
    basic_test = HTTPBasicAuth(testnet_user, testnet_pass)
    logging.info("Updating bearer token..")

    bearer_token_mainnet = get_bearer_token(bearer_api_mainnet_url, basic_prod)
    bearer_token_testnet = get_bearer_token(bearer_api_testnet_url, basic_test)
    print(f"Bearer token mainnet:  {bearer_token_mainnet}"
          f"\nBearer token testnet: {bearer_token_testnet} ")
    if bearer_token_mainnet:
        conf.sudo().set_param("dpd.mainnet.bearer", bearer_token_mainnet)
    if bearer_token_testnet:
        conf.sudo().set_param("dpd.testnet.bearer", bearer_token_testnet)


def send_post_request(data, url, bearer_token, headers=False):
    """
    Sends generic POST request
    :param bearer_token: bearer token response for auth responses
    :param url: target url
    :param data: .json post data
    :param headers: request headers
    :return: json response
    """
    if not headers:
        headers = {'Accept': 'application/json'}
    bearer = {'Authorization': "Bearer " + bearer_token}
    headers.update(bearer)
    _logger.info(f'Sending request to: {url}')

    response = requests.post(url,
                             headers=headers,
                             data=json.dumps(data)
                             )
    if response.ok:
        _logger.info(f"Request ok! : {response.status_code}")
        return response
    else:
        _logger.error(f"Failed to send request {response.status_code}")
        return response


def send_get_url_request(url, bearer_token):
    """
    Sends generic GET request with .../keyword/....
    :param bearer_token: bearer token response for auth responses
    :param url: target url
    :param params: params to get request
    :return: json response
    """
    headers = {'Accept': 'application/json'}
    header_bearer = {'Authorization': "Bearer " + bearer_token}
    headers.update(header_bearer)

    response = requests.get(url,
                            headers=headers,
                            )
    if response.ok:
        _logger.info(f"Request ok! : {response.status_code}")
        return response
    else:
        _logger.error(f"Failed to send request {response.status_code}")
        return response


def send_get_request(params, url, bearer_token):
    """
    Sends generic GET request
    :param bearer_token: bearer token response for auth responses
    :param url: target url
    :param params: params to get request
    :return: json response
    """
    headers = {'Accept': 'application/json'}
    header_bearer = {'Authorization': "Bearer " + bearer_token}
    headers.update(header_bearer)

    response = requests.get(url,
                            headers=headers,
                            params=params
                            )
    if response.ok:
        _logger.info(f"Request ok! : {response.status_code}")
        return response
    else:
        _logger.error(f"Failed to send request {response.status_code}")
        return response


def fill_package_data(self, move_line_wh_packages, package_status: list):
    """
    Fill package delivery data fields in odoo
    :param move_line_wh_packages: list of packages
    :param package_status: list of package data
    """
    _logger.info("Starting filling package data routine...")
    for pick in move_line_wh_packages:
        print(f'{pick.picking_id} {pick.package_number}')
        for package_return_status in package_status:
            if pick.result_package_id.package_number == package_return_status.package_id:
                if hasattr(package_return_status, 'error'):
                    pick.result_package_id.dpd_status = package_return_status.error
                    continue
                else:
                    # Here all data is filled for package
                    pick.result_package_id.dpd_status = package_return_status.status
                    if self:
                        # Don't Show message if triggered from cron job
                        self.message_post(body="Duomenys atnaujinti")
                    # Check when package is processed and when to send Invoice
                    if pick.result_package_id.dpd_status in dpd_in_progress_delivery_statuses:
                        pick.dpd_state = "in_progress"
                        _logger.info("Changing status to waiting")

                    if pick.result_package_id.dpd_status in dpd_done_delivery_statuses:
                        if not pick.result_package_id.is_quotation_sent:
                            _logger.info(
                                f"pick.is_quotation_sent ---disabled---: {pick.result_package_id.is_quotation_sent}")
                            _logger.info("Sending automatic Quotation ---disabled---..")

                            quotation = pick.env['sale.order'].search(
                                [('state', '!=', 'cancel'), ('name', '=', pick.origin)])

                            # Send quotation and add message in chatter
                            # This feature was disabled because client asked for
                            # email_act = quotation.action_quotation_send()
                            # email_ctx = email_act.get('context', {})
                            # quotation.with_context(**email_ctx).message_post_with_template(
                            #     email_ctx.get('default_template_id'))

                            # TODO: if possible check if quotation is set
                            # pack_delivery_object = get_pick_pack_out_ids(self, DeliveryType.OUT)

                            # Set DONE STATUS to /OUT/
                            # TODO: possible find another way of checking sequence_code(can easily change)
                            for pick_pack_out in quotation.picking_ids:
                                if DeliveryType.OUT.name in pick_pack_out.picking_type_id.sequence_code:
                                    logging.info("Setting state OUT state to Done")
                                    pick_pack_out.action_set_quantities_to_reservation()
                                    pick_pack_out._action_done()

                            # This feature was disabled because client asked for
                            pick.result_package_id.is_quotation_sent = True

                        else:
                            _logger.info("Quotation already sent ---disabled---:")

                    pick.result_package_id.dpd_city = package_return_status.country_iso_name
                    pick.result_package_id.dpd_country_code = package_return_status.country_code
                    pick.result_package_id.dpd_country_name = package_return_status.country_name
                    pick.result_package_id.dpd_delivery_estimate = package_return_status.delivery_date
                    pick.result_package_id.dpd_coordinates = (
                        package_return_status.gps_lat, package_return_status.gps_long)
                    pick.result_package_id.dpd_tour = package_return_status.tour
                    pick.result_package_id.dpd_depot = package_return_status.warehouse_code
