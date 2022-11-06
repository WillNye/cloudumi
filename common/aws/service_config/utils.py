import asyncio
import base64
import sys
from itertools import chain
from typing import List

import sentry_sdk

import common.lib.noq_json as json
from common.aws.iam.policy.utils import batch_get_policy_versions, is_tenant_policy
from common.aws.iam.utils import get_tenant_iam_conn
from common.aws.utils import ResourceSummary, get_url_for_resource
from common.config import config
from common.config.models import ModelAdapter
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.aws.session import get_session_for_tenant
from common.lib.generic import un_wrap_json
from common.models import SpokeAccount

MAX_CONFIG_EVENTS_PER_RESOURCE = 50
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
            endpoint_url=f"https://sts.{region}.amazonaws.com",
        ),
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        session_name=sanitize_session_name("noq_aws_config_query"),
    )


async def execute_query(query: str, tenant: str, account_id: str) -> List:
    async def _execute_query(region: str):
        resources_for_region = []
        try:
            config_client = get_config_client(tenant, account_id, region)
            response = config_client.select_resource_config(Expression=query, Limit=100)
            for r in response.get("Results", []):
                resources_for_region.append(json.loads(r))
            # Query Config for a specific account in all regions we care about
            while response.get("NextToken"):
                response = config_client.select_resource_config(
                    Expression=query, Limit=100, NextToken=response["NextToken"]
                )
                for r in response.get("Results", []):
                    resources_for_region.append(json.loads(r))
        except Exception as e:
            log.error(
                {
                    "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                    "message": "Failed to query AWS Config",
                    "query": query,
                    "account_id": account_id,
                    "region": region,
                    "error": str(e),
                    "tenant": tenant,
                },
                exc_info=True,
            )
            sentry_sdk.capture_exception()
        finally:
            return resources_for_region

    session = get_session_for_tenant(tenant)
    available_regions = session.get_available_regions("config")
    excluded_regions = config.get(
        "_global_.api_protect.exclude_regions",
        [
            "af-south-1",
            "ap-east-1",
            "ap-southeast-3",
            "ap-northeast-3",
            "eu-south-1",
            "me-south-1",
        ],
    )
    resources = await asyncio.gather(
        *[_execute_query(x) for x in available_regions if x not in excluded_regions]
    )
    return list(chain.from_iterable(resources))


def get_fetch_parameters_resource_history(
    unique_resource_identifier: str,
) -> any:
    """This is a utility function that pulls out the account id, Region, ResourceType, and ResourceId for the fetch functions."""
    # pylint: disable=R0914,R0912
    # Need to pull out the Account ID, Region, ResourceType, ResourceId:
    account_id, region, resource_type, resource_id = unique_resource_identifier.split(
        "/"
    )  # This should have been validated already.
    try:
        resource_id = base64.urlsafe_b64decode(resource_id).decode(
            "utf-8"
        )  # Un-Base64/URL quote the Resource ID
    except Exception as exc:
        raise (
            f"Resource: {unique_resource_identifier} has an invalid Base64 string in for the Resource ID field."
        ) from exc

    # If we are pulling from a global resource, then we need to override the region to where we are collecting global resources:
    if region == "global":
        region = self.configuration.global_resource_query_region  # noqa

    return account_id, region, resource_type, resource_id


async def get_history_for_managed_policies(
    iam_client, arn_list: list[str]
) -> list[dict]:
    managed_policy_versions = await batch_get_policy_versions(iam_client, arn_list)
    response = list()

    for policy_version_info in managed_policy_versions:
        arn = policy_version_info["arn"]
        name = arn.split("policy/")[-1]
        policy_version = policy_version_info["policy_version"]
        policy_version["document"] = policy_version.pop("Document", {})
        created_at = policy_version.get("CreateDate")
        response.append(
            {
                "version": policy_version.pop("VersionId", None),
                "configurationItemStatus": "OK",
                "configurationItemCaptureTime": created_at,
                "arn": arn,
                "resourceType": "AWS::IAM::Policy",
                "resourceName": name,
                "awsRegion": "global",
                "availabilityZone": "Not Applicable",
                "resourceCreationTime": created_at,
                "tags": {},
                "relatedEvents": [],
                "relationships": [],
                "configuration": {
                    "policyName": name,
                    "arn": arn,
                    "path": "/",
                    "createDate": created_at,
                    "updateDate": created_at,
                    "policyVersionList": [policy_version],
                },
            }
        )

    return un_wrap_json(response)


async def get_config_for_resources(
    config_client, arn_list: list[str], select_fields: list = None
) -> dict:
    select_fields = "*" if not select_fields else ", ".join(select_fields)

    if len(arn_list) > 1:
        arn_list_str = ", ".join([f"'{arn}'" for arn in arn_list])
        query_expr = f"SELECT {select_fields} WHERE arn in ({arn_list_str});"
    else:
        query_expr = f"SELECT {select_fields} WHERE arn = '{arn_list[0]}';"

    response = config_client.select_resource_config(
        Expression=query_expr, Limit=len(arn_list)
    )
    return un_wrap_json(response.get("Results", []))


async def get_resource_history(
    resource_summary: ResourceSummary,
    include_relationships: bool = True,
    max_config_events_per_resource: int = 50,
) -> list[dict]:
    """Retrieve all config changes for a given resource with the ability to also include config changes for related resources"""
    max_config_events_per_resource = min(
        max_config_events_per_resource, MAX_CONFIG_EVENTS_PER_RESOURCE
    )

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

            if len(
                resource_config_changes
            ) >= max_config_events_per_resource or not api_response.get("nextToken"):
                return resource_config_changes
            else:
                config_args["nextToken"] = api_response["nextToken"]

    account = resource_summary.account
    region = resource_summary.region if resource_summary.region else config.region
    tenant = resource_summary.tenant
    config_client = get_config_client(tenant, account, region)
    resource_details = await get_config_for_resources(
        config_client, [resource_summary.arn], ["resourceId", "resourceType"]
    )
    if not resource_details:
        return []

    resource_details = resource_details[0]
    configuration_changes = []
    for config_change in await _get_resource_history(**resource_details):
        configuration_changes.append(
            {
                "config_change": config_change,
                "updated_at": config_change["configurationItemCaptureTime"],
                "rollback_supported": True,
            }
        )

    if include_relationships:
        # Get all arns which have been used as either a permission boundary or managed policy within the last 90 days for the resource
        related_arns = set()
        managed_arns = set()

        for full_config_change in configuration_changes:
            if (
                full_config_change.get("config_change", {}).get(
                    "configurationItemStatus"
                )
                == "ResourceNotRecorded"
            ):
                continue
            config_change = full_config_change["config_change"].get("configuration", {})
            if config_change == "null" or not config_change:
                continue
            for managed_policy in config_change.get("attachedManagedPolicies", []):
                arn = managed_policy["policyArn"]
                if is_tenant_policy(arn):
                    related_arns.add(arn)
                else:
                    managed_arns.add(arn)

            if perm_boundary := config_change.get("permissionsBoundary"):
                arn = perm_boundary["permissionsBoundaryArn"]
                if is_tenant_policy(arn):
                    related_arns.add(arn)
                else:
                    managed_arns.add(arn)

        if related_arns or managed_arns:
            related_configuration_changes = list()

            arn_url_map = dict()
            for related_resource_summary in await ResourceSummary.bulk_set(
                tenant, list(related_arns) + list(managed_arns)
            ):
                arn_url_map[related_resource_summary.arn] = await get_url_for_resource(
                    related_resource_summary
                )

            if related_arns:
                # Get attributes necessary to retrieve history for the related resources (and get that history)
                related_resources = await get_config_for_resources(
                    config_client, list(related_arns), ["resourceId", "resourceType"]
                )
                related_resource_history = await asyncio.gather(
                    *[
                        _get_resource_history(**resource)
                        for resource in related_resources
                    ]
                )
                related_configuration_changes.extend(
                    list(chain.from_iterable(related_resource_history))
                )

            if managed_arns:
                iam_client = get_tenant_iam_conn(
                    tenant, account, "get_managed_policy_history"
                )
                managed_resource_history = await get_history_for_managed_policies(
                    iam_client, list(managed_arns)
                )
                related_configuration_changes.extend(managed_resource_history)

            for config_change in related_configuration_changes:
                configuration_changes.append(
                    {
                        "config_change": config_change,
                        "updated_at": config_change["configurationItemCaptureTime"],
                        "rollback_supported": False,
                        "resource_url": arn_url_map[config_change.get("arn")],
                    }
                )

    return sorted(
        configuration_changes,
        key=lambda x: x["updated_at"],
        reverse=True,
    )
