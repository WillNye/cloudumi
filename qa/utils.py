import json

import requests

from qa import COOKIES, TENANT_API


def generic_api_get_request(endpoint: str, **kwargs):
    response = requests.get(
        f"{TENANT_API}/{endpoint}",
        cookies=COOKIES,
        params=kwargs,
    )
    if not response.ok:
        print(response.text)
        response.raise_for_status()

    response = response.json()
    print(json.dumps(response, indent=2))
    return response
