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
