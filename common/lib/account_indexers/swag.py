import sys
from typing import List

from tornado.httpclient import AsyncHTTPClient, HTTPClientError

import common.lib.noq_json as json
from common.config import config
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib.plugins import get_plugin_by_name
from common.models import CloudAccountModel, CloudAccountModelArray

log = config.get_logger(__name__)
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()


async def retrieve_accounts_from_swag(tenant) -> CloudAccountModelArray:
    function: str = f"{sys._getframe().f_code.co_name}"
    expected_owners: List = config.get_tenant_specific_key(
        "retrieve_accounts_from_swag.expected_owners", tenant, []
    )

    swag_base_url = config.get_tenant_specific_key(
        "retrieve_accounts_from_swag.base_url", tenant
    )
    if not swag_base_url:
        raise MissingConfigurationValue("Unable to find Swag URL in configuration")
    swag_url = swag_base_url + "api/1/accounts"

    try:
        http_client = AsyncHTTPClient(force_instance=True)
        resp = await http_client.fetch(
            swag_url,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

    except (ConnectionError, HTTPClientError) as e:
        log.error(
            {
                "message": "Unable to connect to SWAG",
                "error": str(e),
                "function": function,
            },
            exc_info=True,
        )
        stats.count(f"{function}.connectionerror")
        raise
    swag_accounts = json.loads(resp.body)
    cloud_accounts = []
    for account in swag_accounts:
        # Ignore third party accounts
        if expected_owners and account.get("owner") not in expected_owners:
            continue
        account_status = account["account_status"]
        sync_enabled = False
        if account_status == "ready":
            account_status = "active"
            sync_enabled = True
        cloud_accounts.append(
            CloudAccountModel(
                id=account["id"],
                name=account["name"],
                email=account["email"],
                status=account_status,
                sync_enabled=sync_enabled,
                sensitive=account["sensitive"],
                environment=account["environment"],
                aliases=account["aliases"],
                type="aws",
            )
        )
    return CloudAccountModelArray(accounts=cloud_accounts)
