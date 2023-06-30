import asyncio
from typing import Dict, Optional, Type, Union

from cachetools import TTLCache
from iambic.core.models import BaseTemplate as IambicBaseTemplate
from iambic.core.utils import sanitize_string
from iambic.plugins.v0_1_0.aws.iam.group.models import AWS_IAM_GROUP_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.policy.models import AWS_MANAGED_POLICY_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.role.models import AWS_IAM_ROLE_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.user.models import AWS_IAM_USER_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.identity_center.permission_set.models import \
    AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE
from jinja2 import BaseLoader, Environment
from policy_sentry.util.arns import get_account_from_arn, parse_arn

from common.config import config
from common.lib.cache import retrieve_json_data_from_redis_or_s3

log = config.get_logger(__name__)


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


async def list_tenant_resources(tenant: str) -> list[dict]:
    """
    Returns a list containing summary information of all tenant resources.

    Note: policies is in the keys but this does not represent all resources types contained within the response.
        At the time this was written, this is the list of supported resources -
            S3, Role, SQS, SNS, User, and Policy

    Response Keys: list[
        Dict(
            account_id: str,
            account_name: str,
            arn: str,
            technology: str,
            templated: str,
            errors: int,
            config_history_url: str
        )
    ]
    """

    return await retrieve_json_data_from_redis_or_s3(
        redis_key=config.get_tenant_specific_key(
            "policies.redis_policies_key",
            tenant,
            f"{tenant}_ALL_POLICIES",
        ),
        s3_bucket=config.get_tenant_specific_key(
            "cache_policies_table_details.s3.bucket", tenant
        ),
        s3_key=config.get_tenant_specific_key(
            "cache_policies_table_details.s3.file",
            tenant,
            "policies_table/cache_policies_table_details_v1.json.gz",
        ),
        default=[],
        tenant=tenant,
    )


class ResourceAccountCache:
    _tenant_resources: dict[TTLCache] = {}

    @classmethod
    async def set_tenant_resources(cls, tenant: str) -> TTLCache:
        tenant_resources = await list_tenant_resources(tenant)
        cls._tenant_resources[tenant] = TTLCache(
            maxsize=max(len(tenant_resources), 1000), ttl=120
        )
        for tenant_resource in tenant_resources:
            cls._tenant_resources[tenant][tenant_resource["arn"]] = tenant_resource[
                "account_id"
            ]

        return cls._tenant_resources[tenant]

    @classmethod
    async def get(cls, tenant: str, arn: str) -> str:
        if resource_account := get_account_from_arn(arn):
            return resource_account

        if "s3" in arn:
            bucket_key = config.get_tenant_specific_key(
                "redis.s3_bucket_key", tenant, f"{tenant}_S3_BUCKETS"
            )
            s3_bucket = config.get_tenant_specific_key(
                "account_resource_cache.s3_combined.bucket", tenant
            )
            s3_key = config.get_tenant_specific_key(
                "account_resource_cache.s3_combined.file",
                tenant,
                "account_resource_cache/cache_s3_combined_v1.json.gz",
            )
            try:
                bucket_data = await retrieve_json_data_from_redis_or_s3(
                    redis_key=bucket_key,
                    redis_data_type="hash",
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                    tenant=tenant,
                )
                bucket_name = parse_arn(arn)["resource"]
                resource_accounts = [
                    account_id
                    for account_id, buckets in bucket_data.items()
                    if bucket_name in buckets
                ]
                if resource_accounts:
                    return resource_accounts[0]
            except Exception as exc:
                log.exception(exc)

        if tenant_resources := cls._tenant_resources.get(tenant):
            try:
                return tenant_resources[arn]
            except KeyError:
                tenant_resources = await cls.set_tenant_resources(tenant)
        else:
            tenant_resources = await cls.set_tenant_resources(tenant)

        try:
            return tenant_resources[arn]
        except KeyError:
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

        if not account_provided:
            arn_as_resource = arn
            if parsed_arn["service"] == "s3" and not account_provided:
                arn_as_resource = arn_as_resource.replace(
                    f"/{parsed_arn['resource_path']}", ""
                )

            parsed_arn["account"] = await ResourceAccountCache.get(
                tenant, arn_as_resource
            )
            if account_required and not parsed_arn["account"]:
                raise ValueError(f"Resource account not found - {arn_as_resource}")

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


async def get_resource_arn(
        iambic_provider_def,
        iambic_template: Type[IambicBaseTemplate]
) -> Union[str, None]:
    if iambic_template.template_type == AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE:
        # Not bothering with generating the ARN for this because it isn't being used
        return

    variables = {
        var.key: var.value for var in iambic_provider_def.variables
    }
    variables["account_id"] = iambic_provider_def.account_id
    variables["account_name"] = iambic_provider_def.account_name
    if hasattr(iambic_template, "owner") and (
        owner := getattr(iambic_template, "owner", None)
    ):
        variables["owner"] = owner
    valid_characters_re = r"[\w_+=,.@-]"
    variables = {
        k: sanitize_string(v, valid_characters_re) for k, v in variables.items()
    }

    if iambic_template.template_type == AWS_IAM_GROUP_TEMPLATE_TYPE:
        resource_name = "group"
    elif iambic_template.template_type == AWS_IAM_ROLE_TEMPLATE_TYPE:
        resource_name = "role"
    elif iambic_template.template_type == AWS_IAM_USER_TEMPLATE_TYPE:
        resource_name = "user"
    elif iambic_template.template_type == AWS_MANAGED_POLICY_TEMPLATE_TYPE:
        resource_name = "policy"
    else:
        raise ValueError(f"Unknown template type: {iambic_template.template_type}")

    role_arn = f"arn:aws:iam::{iambic_provider_def.account_id}:{resource_name}{iambic_template.properties.path}{iambic_template.properties.role_name}"
    rtemplate = Environment(loader=BaseLoader()).from_string(role_arn)
    return rtemplate.render(var=variables)
