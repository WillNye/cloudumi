import json
from json import JSONDecodeError
from typing import Union
from urllib.parse import urljoin

import requests

from qa import TENANT_SUMMARY


def sanitize_endpoint(endpoint: str) -> str:
    if not any(endpoint.startswith(prefix) for prefix in ["/api", "api"]):
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        endpoint = f"api/{endpoint}"

    return endpoint


def handle_response(response) -> Union[dict, None]:
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


def generic_api_get_request(endpoint: str, **kwargs) -> dict:
    response = requests.get(
        urljoin(TENANT_SUMMARY.tenant_url, sanitize_endpoint(endpoint)),
        cookies=TENANT_SUMMARY.cookies,
        params=kwargs,
    )
    return handle_response(response)


def generic_api_create_or_update_request(
    http_method: str, endpoint: str, **kwargs
) -> dict:
    # Handles POST, PUT, PATCH
    response = getattr(requests, http_method.lower())(
        urljoin(TENANT_SUMMARY.tenant_url, sanitize_endpoint(endpoint)),
        cookies=TENANT_SUMMARY.cookies,
        json=kwargs,
    )
    return handle_response(response)


def generic_api_delete_request(endpoint: str):
    response = requests.delete(
        urljoin(TENANT_SUMMARY.tenant_url, sanitize_endpoint(endpoint)),
        cookies=TENANT_SUMMARY.cookies,
    )
    return handle_response(response)
