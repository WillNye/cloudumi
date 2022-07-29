import asyncio
import json
from typing import Dict, Optional

from policy_sentry.util.arns import get_account_from_arn, parse_arn

from common.config import config
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.redis import RedisHandler, redis_hget

log = config.get_logger()


def get_resource_tag(
    resource: Dict,
    key: str,
    is_list: Optional[bool] = False,
    default: Optional[any] = None,
) -> any:
    """
    Retrieves and parses the value of a provided AWS tag.
    :param resource: An AWS resource dictionary
    :param key: key of the tag
    :param is_list: The value for the key is a list type
    :param default: Default value is tag not found
    :return:
    """
    for tag in resource.get("Tags", resource.get("tags", [])):
        if tag.get("Key") == key:
            val = tag.get("Value")
            if is_list:
                return set([] if not val else val.split(":"))
            return val
    return default


async def get_resource_account(arn: str, tenant: str) -> str:
    """Return the AWS account ID that owns a resource.

    In most cases, this will pull the ID directly from the ARN.
    If we are unsuccessful in pulling the account from ARN, we try to grab it from our resources cache
    """
    red = await RedisHandler().redis(tenant)
    resource_account: str = get_account_from_arn(arn)
    if resource_account:
        return resource_account

    resources_from_aws_config_redis_key: str = config.get_tenant_specific_key(
        "aws_config_cache.redis_key",
        tenant,
        f"{tenant}_AWSCONFIG_RESOURCE_CACHE",
    )

    if not red.exists(resources_from_aws_config_redis_key):
        # This will force a refresh of our redis cache if the data exists in S3
        await retrieve_json_data_from_redis_or_s3(
            redis_key=resources_from_aws_config_redis_key,
            s3_bucket=config.get_tenant_specific_key(
                "aws_config_cache_combined.s3.bucket", tenant
            ),
            s3_key=config.get_tenant_specific_key(
                "aws_config_cache_combined.s3.file",
                tenant,
                "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
            ),
            redis_data_type="hash",
            tenant=tenant,
            default={},
        )

    resource_info = await redis_hget(resources_from_aws_config_redis_key, arn, tenant)
    if resource_info:
        return json.loads(resource_info).get("accountId", "")
    elif "arn:aws:s3:::" in arn:
        # Try to retrieve S3 bucket information from S3 cache. This is inefficient and we should ideally have
        # retrieved this info from our AWS Config cache, but we've encountered problems with AWS Config historically
        # that have necessitated this code.
        s3_cache = await retrieve_json_data_from_redis_or_s3(
            redis_key=config.get_tenant_specific_key(
                "redis.s3_buckets_key", tenant, f"{tenant}_S3_BUCKETS"
            ),
            redis_data_type="hash",
            tenant=tenant,
        )
        search_bucket_name = arn.split(":")[-1]
        for bucket_account_id, buckets in s3_cache.items():
            buckets_j = json.loads(buckets)
            if search_bucket_name in buckets_j:
                return bucket_account_id
    return ""


class ResourceSummary:
    def __init__(
        self,
        tenant: str,
        arn: str,
        account: str,
        partition: str,
        service: str,
        region: str,
        resource_type: str,
        name: str,
        parent_name: str = None,
        path: str = "/",
    ):
        self.tenant = tenant
        self.arn = arn
        self.account = account
        self.partition = partition
        self.service = service
        self.region = region
        self.resource_type = resource_type
        self.name = name
        self.parent_name = parent_name
        self.path = path

    @classmethod
    async def set(
        cls,
        tenant: str,
        arn: str,
        region_required: bool = False,
        account_required: bool = True,
    ) -> "ResourceSummary":
        # TODO: Handle gov and china ARNs
        from common.lib.aws.utils import get_bucket_location_with_fallback

        parsed_arn = parse_arn(arn)
        parsed_arn["arn"] = arn
        account_provided = bool(parsed_arn["account"])
        content_set = False

        if not account_provided and account_required:
            arn_as_resource = arn
            if parsed_arn["service"] == "s3" and not account_provided:
                arn_as_resource = arn_as_resource.replace(
                    f"/{parsed_arn['resource_path']}", ""
                )

            parsed_arn["account"] = await get_resource_account(arn_as_resource, tenant)
            if not parsed_arn["account"]:
                raise ValueError("Resource account not found")

        if parsed_arn["service"] == "s3":
            parsed_arn["name"] = parsed_arn.pop("resource_path", None)

            if not account_provided:  # Either a bucket or an object
                content_set = True
                bucket_name = parsed_arn.pop("resource", "")
                if parsed_arn["name"]:
                    parsed_arn["resource_type"] = "object"
                    parsed_arn["parent_name"] = bucket_name
                else:
                    parsed_arn["resource_type"] = "bucket"
                    parsed_arn["name"] = bucket_name

                if not region_required or bucket_name == "*":
                    parsed_arn["region"] = ""
                else:
                    parsed_arn["region"] = await get_bucket_location_with_fallback(
                        bucket_name, parsed_arn["account"], tenant
                    )

        if not content_set:
            if not parsed_arn["region"]:
                parsed_arn["region"] = config.region

            if resource_path := parsed_arn.pop("resource_path", ""):
                if "/" in resource_path:
                    split_path = resource_path.split("/")
                    parsed_arn["name"] = split_path[-1]
                    resource_path = "/".join(split_path[:-1])
                    parsed_arn["path"] = f"/{resource_path}/"
                else:
                    parsed_arn["name"] = resource_path

                parsed_arn["resource_type"] = parsed_arn.pop("resource", "")
            else:
                parsed_arn["name"] = parsed_arn.pop("resource", "")
                parsed_arn["resource_type"] = parsed_arn["service"]

        return cls(tenant, **parsed_arn)

    @property
    def full_name(self):
        if self.resource_type == "policy" and self.path:
            return f"{self.path}/{self.name}"
        return self.name

    @classmethod
    async def bulk_set(
        cls,
        tenant: str,
        arn_list: list[str],
        region_required: bool = False,
        account_required: bool = True,
    ) -> list["ResourceSummary"]:
        return await asyncio.gather(
            *[
                cls.set(tenant, arn, region_required, account_required)
                for arn in arn_list
            ]
        )


async def get_url_for_resource(resource_summary: ResourceSummary):
    service = resource_summary.service
    account = resource_summary.account
    region = resource_summary.region
    resource_type = resource_summary.resource_type
    name = resource_summary.name

    url = ""
    if (service == "iam" and resource_type == "role") or service == "AWS::IAM::Role":
        url = f"/policies/edit/{account}/iamrole/{name}"
    elif service == "iam" and resource_type == "policy" and account != "aws":
        url = f"/policies/edit/{account}/managed_policy/{name}"
    elif service in ["s3", "AWS::S3::Bucket"]:
        url = f"/policies/edit/{account}/s3/{name}"
    elif service == "managed_policy":
        # managed policies can have a path
        url = f"/policies/edit/{account}/managed_policy/{resource_type}/{name}"
    elif service in ["sns", "AWS::SNS::Topic"]:
        url = f"/policies/edit/{account}/sns/{region}/{name}"
    elif service in ["sqs", "AWS::SQS::Queue"]:
        url = f"/policies/edit/{account}/sqs/{region}/{name}"
    elif (service == "AWS::CloudFormation::Stack") or (
        service == "cloudformation" and resource_type == "stack"
    ):
        url = f"/role/{account}?redirect=https://console.aws.amazon.com/cloudformation/home?region={region}#/stacks/"
    elif service == "AWS::CloudFront::Distribution" or (
        service == "cloudfront" and resource_type == "distribution"
    ):
        url = f"/role/{account}?redirect=https://console.aws.amazon.com/cloudfront/home?%23distribution-settings:{name}"
    elif service == "AWS::CloudTrail::Trail" or (
        service == "cloudtrail" and resource_type == "trail"
    ):
        url = f"/role/{account}?redirect=https://console.aws.amazon.com/cloudtrail/home?region={region}%23/configuration"
    elif service == "AWS::CloudWatch::Alarm" or (
        service == "cloudwatch" and resource_type == "alarm"
    ):
        url = (
            f"/role/{account}?redirect=https://console.aws.amazon.com/cloudwatch/home"
            f"?region={region}%23alarmsV2:"
        )
    elif service == "AWS::CodeBuild::Project" or (
        service == "codebuild" and resource_type == "project"
    ):
        url = (
            f"/role/{account}?redirect=https://console.aws.amazon.com/codesuite/codebuild/"
            f"{account}/projects/{name}/history?region={region}"
        )
    elif service == "AWS::CodePipeline::Pipeline" or service == "codepipeline":
        url = (
            f"/role/{account}?redirect="
            "https://console.aws.amazon.com/codesuite/codepipeline/pipelines/"
            f"{name}/view?region={region}"
        )
    elif service == "AWS::DynamoDB::Table" or (
        service == "dynamodb" and resource_type == "table"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/dynamodb/home?region={region}%23tables:selected={name}"
        )
    elif service == "AWS::EC2::CustomerGateway" or (
        service == "ec2" and resource_type == "customer-gateway"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23CustomerGateways:search={name}"
        )
    elif service == "AWS::EC2::InternetGateway" or (
        service == "ec2" and resource_type == "internet-gateway"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23igws:search={name}"
        )
    elif service == "AWS::EC2::NatGateway" or (
        service == "ec2" and resource_type == "natgateway"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23NatGateways:search={name}"
        )
    elif service == "AWS::EC2::NetworkAcl" or (
        service == "ec2" and resource_type == "network-acl"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23acls:search={name}"
        )
    elif service == "AWS::EC2::RouteTable" or (
        service == "ec2" and resource_type == "route-table"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23RouteTables:search={name}"
        )
    elif service == "AWS::EC2::SecurityGroup" or (
        service == "ec2" and resource_type == "security-group"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/ec2/v2/home?region={region}%23SecurityGroup:groupId={name}"
        )
    elif service == "AWS::EC2::Subnet" or (
        service == "ec2" and resource_type == "subnet"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23subnets:search={name}"
        )
    elif service == "AWS::EC2::VPC" or (service == "ec2" and resource_type == "vpc"):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23vpcs:search={name}"
        )
    elif service == "AWS::EC2::VPCEndpoint" or (
        service == "ec2" and resource_type == "vpc-endpoint"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23Endpoints:search={name}"
        )
    elif service == "AWS::EC2::VPCEndpointService" or (
        service == "ec2" and resource_type == "vpc-endpoint-service"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23EndpointServices:search={name}"
        )
    elif service == "AWS::EC2::VPCPeeringConnection" or (
        service == "ec2" and resource_type == "vpc-peering-connection"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23PeeringConnections:search={name}"
        )
    elif service == "AWS::EC2::VPNConnection" or (
        service == "ec2" and resource_type == "vpn-connection"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23VpnConnections:search={name}"
        )
    elif service == "AWS::EC2::VPNGateway" or (
        service == "ec2" and resource_type == "vpn-gateway"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/vpc/home?region={region}%23VpnGateways:search={name}"
        )
    elif service == "AWS::ElasticBeanstalk::Application" or (
        service == "elasticbeanstalk" and resource_type == "application"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/elasticbeanstalk/home?region={region}%23/applications"
        )
    elif service == "AWS::ElasticBeanstalk::ApplicationVersion" or (
        service == "elasticbeanstalk" and resource_type == "applicationversion"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/elasticbeanstalk/home?region={region}%23/applications"
        )
    elif service == "AWS::ElasticBeanstalk::Environment" or (
        service == "elasticbeanstalk" and resource_type == "environment"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/elasticbeanstalk/home?region={region}%23/environments"
        )
    elif service == "AWS::ElasticLoadBalancing::LoadBalancer" or (
        service == "elasticloadbalancing"
        and resource_type == "loadbalancer"
        and "/app/" not in resource_summary.arn
    ):
        url = (
            f"/role/{account}?redirect="
            "https://console.aws.amazon.com"
            f"/ec2/v2/home?region={region}%23LoadBalancers:search={name}"
        )
    elif service == "AWS::ElasticLoadBalancingV2::LoadBalancer" or (
        service == "elasticloadbalancing" and resource_type == "loadbalancer"
    ):
        url = (
            f"/role/{account}?redirect="
            "https://console.aws.amazon.com"
            f"/ec2/v2/home?region={region}%23LoadBalancers:search={name}"
        )
    elif service == "AWS::Elasticsearch::Domain" or (
        service == "es" and resource_type == "domain"
    ):
        url = (
            f"/role/{account}?redirect="
            "https://console.aws.amazon.com"
            f"/es/home?region={region}%23domain:resource={name};action=dashboard;tab=undefined"
        )
    elif service == "AWS::Lambda::Function" or (
        service == "lambda" and resource_type == "function"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/lambda/home?region={region}%23/functions/{name}"
        )
    elif service == "AWS::RDS::DBSnapshot" or (
        service == "rds" and resource_type == "snapshot"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/rds/home?region={region}%23db-snapshot:id={name}"
        )
    # TBD
    elif service == "AWS::Redshift::Cluster":
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/rds/home?region={region}%23db-snapshot:id={name}"
        )
    elif service == "AWS::IAM::Policy" or (
        service == "iam" and resource_type == "policy"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/iam/home?%23/policies/{resource_summary.arn}$serviceLevelSummary"
        )
    elif service == "AWS::IAM::User" or (service == "iam" and resource_type == "user"):
        url = f"/policies/edit/{account}/iamuser/{name}"
    elif service == "AWS::IAM::Group" or (
        service == "iam" and resource_type == "group"
    ):
        url = f"/role/{account}?redirect=https://console.aws.amazon.com/iam/home?%23/groups/{name}"
    elif service == "AWS::Shield::Protection":
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/wafv2/shield%23/tedx"
        )
    elif service == "AWS::ShieldRegional::Protection" or (
        service == "shield" and resource_type == "protection"
    ):
        url = (
            f"/role/{account}?redirect="
            f"https://console.aws.amazon.com/wafv2/shield%23/tedx"
        )
    elif service in ["AWS::WAF::RateBasedRule", "AWS::WAF::Rule"] or (
        service == "waf" and resource_type in ["rule", "ratebasedrule"]
    ):
        url = f"/role/{account}?redirect=" f"https://console.aws.amazon.com/wafv2/home"
    elif service == "AWS::WAF::RuleGroup" or (
        service in ["waf", "wafv2"] and "rulegroup/" in resource_summary.arn
    ):
        url = f"/role/{account}?redirect=" f"https://console.aws.amazon.com/wafv2/fms"
    elif service == "AWS::WAF::WebACL" or (
        service in ["waf", "wafv2"] and "webacl/" in resource_summary.arn
    ):
        url = f"/role/{account}?redirect=" f"https://console.aws.amazon.com/wafv2/home"

    return url
