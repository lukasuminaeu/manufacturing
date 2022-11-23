import json
import logging
import os
from enum import Enum
from os.path import join, dirname
from pprint import pprint

import requests
from dotenv import load_dotenv, find_dotenv
from requests.auth import HTTPBasicAuth

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

load_dotenv(find_dotenv())

_logger = logging.getLogger(__name__)

BEARER_TOKEN_TEST = os.environ.get("BEARER_TOKEN_TEST")
BEARER_TOKEN_PRODUCTION = os.environ.get("BEARER_PRODUCTION")

AUTH_USER_TEST = os.environ.get("AUTH_USER_TEST")
AUTH_PASS_TEST = os.environ.get("AUTH_PASS_TEST")
basic_test = HTTPBasicAuth(AUTH_USER_TEST, 'AUTH_PASS_TEST')

AUTH_USER_PROD = os.environ.get("AUTH_USER_PROD")
AUTH_PASS_PROD = os.environ.get("AUTH_PASS_PROD")
basic_prod = HTTPBasicAuth(AUTH_USER_PROD, AUTH_PASS_PROD)

URL_BASE_TEST = "https://sandbox-esiunta.dpd.lt/api/v1"
URL_BASE_PROD = "https://esiunta.dpd.lt/api/v1"
URL_PARCEL_PROD_STATUS = "https://status.dpd.lt/external/tracking"


class PackageStatus:
    package_id: str
    status: str

    def __str__(self):
        return f'PackageStatus(package_id={str(self.package_id)} '

    def __repr__(self):
        return f'PackageStatus(package_id={str(self.package_id)} '


class StatusDetail(Enum):
    BASIC = 0
    ADVANCED = 3


def send_get_package_status(bearer: str, packages: list, language="lt", detail=StatusDetail.BASIC, show_all=False):
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
                if package.get("details"):
                    pk_obj.status_obj = send_get_package_status(packages=[package.get("parcelNumber")], bearer=bearer,
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
                if package.get("details"):
                    pk_obj.status_obj = send_get_package_status(packages=[package.get("parcelNumber")], bearer=bearer,
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


def get_bearer_token(url_base, auth):
    """
    Receive bearer token for further authentication
    :return: bearer token
    """

    payload = {
        "name": "Unima 2022-04-05",
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
        return False


def post_shipping(base_url, bearer_token):
    """Post basic shipment to dpd"""
    endpoint = "/shipments"
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    bearer = {'Authorization': "Bearer " + bearer_token}
    headers.update(bearer)

    sender_address = {
        "senderAddress": {
            "name": "Test Sender",
            "email": "example@example.com",
            "phone": "+37112345678",
            "street": "Rygos",
            "streetNo": "56",
            "city": "Vilnius",
            "postalCode": "1005",
            "country": "LT"
        }}
    receiver_address = {
        "receiverAddress": {
            "name": "Test Receiver",
            "email": "example@example.com",
            "phone": "+37112345678",
            "street": "Sauletekio",
            "streetNo": "15a",
            "city": "Vilnius",
            "postalCode": "05123",
            "country": "LT"
        }}
    packages = {
        "parcels": [
            {
                "weight": 1.2,
                "mpsReferences": [
                    "Parcel reference 1",
                    "Parcel reference 2",
                    "Parcel reference 3",
                    "Parcel reference 4"
                ]
            },
            {
                "weight": 2.3
            }
        ]}
    service = {
        "service": {
            "serviceAlias": "DPD CLASSIC"
            # "serviceAlias": "B2C"
        }}
    new_shipment = [{**sender_address, **receiver_address, **packages, **service}]
    r = requests.post(base_url + endpoint,
                      headers=headers,
                      data=json.dumps(new_shipment)
                      )

    if r.status_code == 200:
        print("Request ok")

    else:
        print(r.status_code)
        pprint(json.loads(r.content))


if __name__ == "__main__":
    # print("Executed when invoked directly")
    # print(get_bearer_token(URL_BASE_TEST, auth=basic))
    # print(get_bearer_token(URL_BASE_PROD, auth=basic_prod))

    # Statusas: Vežama
    # Siuntos Nr.: 05818022512763
    # https://esiunta.dpd.lt/contracted/shipments/10505875

    # Statusas: Pristatyta gavėjui
    # Siuntos Nr.: 05818022512746
    # https://esiunta.dpd.lt/contracted/shipments/10404619

    # status = send_get_package_status(packages=['05818022512763', '05818022512746'], bearer=BEARER_TOKEN_PRODUCTION,
    #                                  detail=StatusDetail.ADVANCED, show_all=True)
    #
    # status_basic = send_get_package_status(packages=['05818022512787'], bearer=BEARER_TOKEN_PRODUCTION,
    #                                        detail=StatusDetail.BASIC)
    # print(status_basic[0].status)
    # print(post_shipping(URL_BASE_TEST, BEARER_TOKEN_TEST))
    bearer_api_mainnet_url = "https://esiunta.dpd.lt/api/v1"
    bearer_api_testnet_url = "https://sandbox-esiunta.dpd.lt/api/v1"
    BEARER_TOKEN_PRODUCTION_INCORRECT = BEARER_TOKEN_PRODUCTION + "wrong_bearer"
    print(a)
else:
    print("Executed when imported")
