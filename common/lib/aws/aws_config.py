import sys
from typing import List, Optional

import sentry_sdk
from botocore.exceptions import ClientError

import common.lib.noq_json as json
from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import MissingConfigurationValue
from common.lib.assume_role import boto3_cached_conn
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.aws.session import get_session_for_tenant
from common.models import SpokeAccount

log = config.get_logger()


def query(
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


def get_fetch_parameters_resource_history(
    unique_resource_identifier: str,
) -> Tuple[AccountId, Region, ResourceType, ResourceId]:
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
        raise InvalidUniqueResourceIdException(
            f"Resource: {unique_resource_identifier} has an invalid Base64 string in for the Resource ID field."
        ) from exc

    # If we are pulling from a global resource, then we need to override the region to where we are collecting global resources:
    if region == "global":
        region = self.configuration.global_resource_query_region  # noqa

    return account_id, region, resource_type, resource_id


def get_resource_history(tenant, account_id, region, resource_type, resource_id):
    """Loop to fetch a proper amount of AWS Config resource histories.

    Note: This will raise exceptions and will need to be handled by the function that calls this."""
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
        client_kwargs=config.get_tenant_specific_key("boto3.client_kwargs", tenant, {}),
        session_name=sanitize_session_name("noq_aws_config_query"),
    )

    config_args = {
        "resourceType": resource_type,
        "resourceId": resource_id,
        "limit": 25,
        "account_number": account_id,
        "region": region,
        "assume_role": "",
        "session_name": "noq_aws_config_timeline",
        "sts_client_kwargs": {
            "endpoint_url": f"https://sts.{region}.amazonaws.com",
            "region_name": region,
        },
        # For STS V2 tokens
    }

    # You shouldn't get both a revision_id and a next_page (verified by the API)
    if revision_id:
        config_args.update({"earlierTime": before, "laterTime": after})
    elif next_page:
        config_args["nextToken"] = next_page

    configuration_items = []
    while True:
        api_response = config_client.get_resource_config_history(**config_args)

        # Did we get any results?
        if not api_response["configurationItems"]:
            api_response[
                "nextToken"
            ] = None  # Blank out the nextToken since AWS Config likes to keep returning it :/
            break

        configuration_items += api_response["configurationItems"]

        # If we have more results, we are only done if we have at least "max_items" items in our list:
        if api_response.get("nextToken") and len(configuration_items) < max_items:
            config_args["nextToken"] = api_response["nextToken"]

        # If we didn't get any more pages, or we got more than 5 results, then we are done:
        else:
            break  # pragma: no cover  (this is actually covered but not seen by coverage for some reason...)
    return api_response, configuration_items

    # Add in revision ID info if needed (need to subtract by 1 second so that it's included in the result):
    if revision_id:
        config_args.update(
            {
                "earlierTime": datetime.datetime.fromisoformat(start_revision_id)
                - datetime.timedelta(seconds=1)
            }
        )
    # get_resource_config_history
    pass
