from typing import Set

import boto3
import sentry_sdk

from common.config import config
from common.config.models import ModelAdapter
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.sanitize import sanitize_session_name
from common.models import SpokeAccount

log = config.get_logger()


async def get_supported_resource_types() -> Set[str]:
    valid_resource_types = set()
    cf_client = await aio_wrapper(boto3.client, "cloudformation")

    next_token = None
    while True:
        args = dict(
            Visibility="PUBLIC",
            ProvisioningType="FULLY_MUTABLE",
            DeprecatedStatus="LIVE",
            Type="RESOURCE",
            MaxResults=100,
        )
        if next_token:
            args["NextToken"] = next_token
        response = await aio_wrapper(cf_client.list_types, **args)
        for type_summary in response["TypeSummaries"]:
            valid_resource_types.add(type_summary["TypeName"])
        next_token = response.get("NextToken")
        if not next_token:
            break
    return valid_resource_types


async def list_resource_type(host, account_id, region, resource_type):
    resources = []
    cc_client = boto3_cached_conn(
        "cloudcontrol",
        host,
        account_number=account_id,
        assume_role=ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name,
        region=region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        session_name=sanitize_session_name("cloudcontrol_list_resource_type"),
    )
    next_token = ""
    while next_token is not None:
        args = dict(
            TypeName=resource_type,
            MaxResults=100,
        )

        if next_token:
            args["NextToken"] = next_token
        try:
            response = cc_client.list_resources(**args)
            resources.extend(response["ResourceDescriptions"])
            next_token = response.get("NextToken")
            if not next_token:
                break
        except Exception as e:
            log.error({"error": str(e)})
            sentry_sdk.capture_exception()
            break

    return resources


async def list_all_resources(host, account_id, region):
    valid_resource_types = await get_supported_resource_types()
    for resource_type in valid_resource_types:
        # TODO: Convert to async celery task. Task should store result in DDB
        await list_resource_type(host, account_id, region, resource_type)


# async_to_sync(list_all_resources)("localhost", "259868150464", "us-east-1")
