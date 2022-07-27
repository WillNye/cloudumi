import asyncio
import sys
from itertools import chain
from typing import List, Optional

import sentry_sdk
from botocore.exceptions import ClientError

import common.lib.noq_json as json
from common.aws.utils import ResourceSummary
from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.aws.session import get_session_for_tenant
from common.lib.generic import un_wrap_json
from common.models import SpokeAccount

log = config.get_logger()


def get_config_client(tenant: str, account: str, region: str = config.region):
    spoke_account_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", tenant)
        .with_query({"account_id": account})
        .first.name
    )
    return boto3_cached_conn(
        "config",
        tenant,
        None,
        account_number=account,
        assume_role=spoke_account_name,
        region=region,
        sts_client_kwargs=dict(
            region_name=region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        session_name=sanitize_session_name("noq_aws_config_query"),
    )


def execute_query(
    query: str,
    tenant: str,
    use_aggregator: bool = True,
    account_id: Optional[str] = None,
) -> List:
    resources = []
    session = get_session_for_tenant(tenant)
    if use_aggregator:
        config_client = session.client(
            "config",
            region_name=config.region,
            **config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        )
        configuration_aggregator_name: str = config.get_tenant_specific_key(
            "aws_config.configuration_aggregator.name", tenant
        ).format(region=config.region)
        if not configuration_aggregator_name:
            raise MissingConfigurationValue("Invalid configuration for aws_config")
        response = config_client.select_aggregate_resource_config(
            Expression=query,
            ConfigurationAggregatorName=configuration_aggregator_name,
            Limit=100,
        )
        for r in response.get("Results", []):
            resources.append(json.loads(r))
        while response.get("NextToken"):
            response = config_client.select_aggregate_resource_config(
                Expression=query,
                ConfigurationAggregatorName=configuration_aggregator_name,
                Limit=100,
                NextToken=response["NextToken"],
            )
            for r in response.get("Results", []):
                resources.append(json.loads(r))
        return resources
    else:  # Don't use Config aggregator and instead query all the regions on an account
        available_regions = session.get_available_regions("config")
        excluded_regions = config.get(
            "_global_.api_protect.exclude_regions",
            ["af-south-1", "ap-east-1", "ap-northeast-3", "eu-south-1", "me-south-1"],
        )
        regions = [x for x in available_regions if x not in excluded_regions]
        for region in regions:
            config_client = boto3_cached_conn(
                "config",
                tenant,
                None,
                account_number=account_id,
                assume_role=ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", tenant)
                .with_query({"account_id": account_id})
                .first.name,
                region=region,
                sts_client_kwargs=dict(
                    region_name=config.region,
                    endpoint_url=f"https://sts.{config.region}.amazonaws.com",
                ),
                client_kwargs=config.get_tenant_specific_key(
                    "boto3.client_kwargs", tenant, {}
                ),
                session_name=sanitize_session_name("noq_aws_config_query"),
            )
            try:
                response = config_client.select_resource_config(
                    Expression=query, Limit=100
                )
                for r in response.get("Results", []):
                    resources.append(json.loads(r))
                # Query Config for a specific account in all regions we care about
                while response.get("NextToken"):
                    response = config_client.select_resource_config(
                        Expression=query, Limit=100, NextToken=response["NextToken"]
                    )
                    for r in response.get("Results", []):
                        resources.append(json.loads(r))
            except ClientError as e:
                log.error(
                    {
                        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                        "message": "Failed to query AWS Config",
                        "query": query,
                        "use_aggregator": use_aggregator,
                        "account_id": account_id,
                        "region": region,
                        "error": str(e),
                        "tenant": tenant,
                    },
                    exc_info=True,
                )
                sentry_sdk.capture_exception()
        return resources


async def get_resource_config(
    resource_summary: ResourceSummary, select_fields: list = None, config_client=None
) -> dict:
    tenant = resource_summary.tenant
    arn = resource_summary.arn
    account = resource_summary.account
    region = resource_summary.region if resource_summary.region else config.region
    if not config_client:
        config_client = get_config_client(tenant, account, region)

    select_fields = "*" if not select_fields else ", ".join(select_fields)
    response = config_client.select_resource_config(
        Expression=f"SELECT {select_fields} WHERE arn = '{arn}';", Limit=1
    )
    if results := response.get("Results", None):
        return un_wrap_json(results[0])


async def get_resource_history(
    resource_summary: ResourceSummary, include_relationships: bool = True
) -> list[dict]:
    """Retrieve all config changes for a given resource with the ability to also include config changes for related resources"""

    async def _get_resource_history(resourceId, resourceType, **kwargs):
        resource_config_changes = []
        config_args = {
            "resourceId": resourceId,
            "resourceType": resourceType,
            "limit": 10,
        }

        while True:
            api_response = await aio_wrapper(
                config_client.get_resource_config_history, **config_args
            )
            if not api_response["configurationItems"]:
                api_response[
                    "nextToken"
                ] = None  # Blank out the nextToken since AWS Config likes to keep returning it :/
                return resource_config_changes

            resource_config_changes.extend(
                [
                    un_wrap_json(config_change)
                    for config_change in api_response["configurationItems"]
                ]
            )

            if api_response.get("nextToken"):
                config_args["nextToken"] = api_response["nextToken"]
            else:
                return resource_config_changes

    account = resource_summary.account
    region = resource_summary.region if resource_summary.region else config.region
    tenant = resource_summary.tenant
    config_client = get_config_client(tenant, account, region)
    resource_details = await get_resource_config(
        resource_summary, ["relationships", "resourceId", "resourceType"], config_client
    )

    if include_relationships:
        all_resources = [
            related_resource
            for related_resource in resource_details.pop("relationships", [])
        ]
        all_resources.append(resource_details)
        configuration_changes = await asyncio.gather(
            *[_get_resource_history(**resource) for resource in all_resources]
        )
        configuration_changes = list(chain.from_iterable(configuration_changes))
    else:
        configuration_changes = await _get_resource_history(**resource_details)

    return sorted(
        configuration_changes,
        key=lambda x: x["configurationItemCaptureTime"],
        reverse=True,
    )
