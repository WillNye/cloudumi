import json
from json import JSONDecodeError

import requests

from qa import COOKIES, TENANT_API


def handle_response(response):
    if not response.ok:
        print(response.text)
        response.raise_for_status()

    if response.status_code == 200:
        try:
            response = response.json()
            print(json.dumps(response, indent=2))
            return response
        except JSONDecodeError:
            return


def generic_api_get_request(endpoint: str, **kwargs):
    response = requests.get(
        f"{TENANT_API}/{endpoint}",
        cookies=COOKIES,
        params=kwargs,
    )
    return handle_response(response)


def generic_api_create_or_update_request(http_method: str, endpoint: str, **kwargs):
    # Handles POST, PUT, PATCH
    response = getattr(requests, http_method)(
        f"{TENANT_API}/{endpoint}",
        cookies=COOKIES,
        json=kwargs,
    )
    return handle_response(response)


def generic_api_delete_request(endpoint: str):
    response = requests.delete(
        f"{TENANT_API}/{endpoint}",
        cookies=COOKIES,
    )
    return handle_response(response)
