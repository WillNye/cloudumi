import json
import sys
from datetime import datetime, timedelta

from botocore.exceptions import ClientError
from pynamodax.attributes import ListAttribute, NumberAttribute, UnicodeAttribute

from common.aws.iam.role.utils import (
    _clone_iam_role,
    _create_iam_role,
    _delete_iam_role,
    _get_iam_role_async,
    _get_iam_role_sync,
)
from common.aws.iam.utils import _cloudaux_to_aws
from common.config import config
from common.config.config import (
    dax_endpoints,
    dynamodb_host,
    get_dynamo_table_name,
    get_logger,
)
from common.config.models import ModelAdapter
from common.lib.plugins import get_plugin_by_name
from common.lib.pynamo import NoqMapAttribute, NoqModel
from common.models import CloneRoleRequestModel, RoleCreationRequestModel, SpokeAccount

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = get_logger(__name__)


class TagMap(NoqMapAttribute):
    Key = UnicodeAttribute()
    Value = UnicodeAttribute()


class IAMRole(NoqModel):
    class Meta:
        host = dynamodb_host
        table_name = get_dynamo_table_name("iamroles_multitenant")
        dax_write_endpoints = dax_endpoints
        dax_read_endpoints = dax_endpoints
        fallback_to_dynamodb = True

    host = UnicodeAttribute(hash_key=True)
    entity_id = UnicodeAttribute(range_key=True)
    accountId = UnicodeAttribute()
    name = UnicodeAttribute()
    arn = UnicodeAttribute()
    owner = UnicodeAttribute(null=True)
    policy = UnicodeAttribute()
    resourceId = UnicodeAttribute()
    templated = UnicodeAttribute(null=True)
    permissions_boundary = NoqMapAttribute(null=True)
    tags = ListAttribute(of=TagMap, null=True)
    ttl = NumberAttribute()
    last_updated = NumberAttribute()

    @property
    def role_id(self):
        return f"{self.arn}||{self.host}"

    @property
    def assume_role_policy(self):
        return self.policy.get("AssumeRolePolicyDocument")

    @classmethod
    async def get(
        cls,
        account_id: str,
        host: str,
        arn: str,
        force_refresh: bool = False,
        run_sync: bool = False,
    ):
        from common.lib.aws.utils import get_aws_principal_owner

        stat_tags = {
            "account_id": account_id,
            "role_arn": arn,
            "host": host,
        }
        log_data: dict = {
            "function": f"{sys._getframe().f_code.co_name}",
            "role_arn": arn,
            "account_id": account_id,
            "force_refresh": force_refresh,
            "host": host,
        }
        iam_role = None
        entity_id = f"{arn}||{host}"

        if not force_refresh:
            iam_role = await super(IAMRole, cls).get(host, entity_id)

        if not iam_role:
            if force_refresh:
                log_data["message"] = "Force refresh is enabled. Going out to AWS."
                stats.count("aws.fetch_iam_role.force_refresh", tags=stat_tags)
            else:
                log_data["message"] = "Role is missing in DDB. Going out to AWS."
                stats.count("aws.fetch_iam_role.missing_dynamo", tags=stat_tags)
            log.debug(log_data)

            try:
                role_name = arn.split("/")[-1]
                conn = {
                    "account_number": account_id,
                    "assume_role": ModelAdapter(SpokeAccount)
                    .load_config("spoke_accounts", host)
                    .with_query({"account_id": account_id})
                    .first.name,
                    "region": config.region,
                    "client_kwargs": config.get_host_specific_key(
                        "boto3.client_kwargs", host, {}
                    ),
                }
                if run_sync:
                    role = _get_iam_role_sync(account_id, role_name, conn, host)
                else:
                    role = await _get_iam_role_async(account_id, role_name, conn, host)

            except ClientError as ce:
                if ce.response["Error"]["Code"] == "NoSuchEntity":
                    # The role does not exist:
                    log_data["message"] = "Role does not exist in AWS."
                    log.error(log_data)
                    stats.count("aws.fetch_iam_role.missing_in_aws", tags=stat_tags)
                    return None

                else:
                    log_data["message"] = f"Some other error: {ce.response}"
                    log.error(log_data)
                    stats.count(
                        "aws.fetch_iam_role.aws_connection_problem", tags=stat_tags
                    )
                    raise

            # Format the role for DynamoDB and Redis:
            await _cloudaux_to_aws(role)

            last_updated: int = int((datetime.utcnow()).timestamp())
            iam_role = cls(
                arn=role.get("Arn"),
                entity_id=entity_id,
                host=host,
                name=role.get("RoleName"),
                resourceId=role.get("RoleId"),
                accountId=account_id,
                tags=[TagMap(**tag) for tag in role.get("Tags", [])],
                policy=cls().dump_json_attr(role),
                permissions_boundary=role.get("PermissionsBoundary", {}),
                owner=get_aws_principal_owner(role, host),
                templated=role.get("Arn").lower(),
                last_updated=last_updated,
                ttl=int((datetime.utcnow() + timedelta(hours=6)).timestamp()),
            )
            await iam_role.save()

            log_data["message"] = "Role fetched from AWS, and synced with DDB."
            stats.count(
                "aws.fetch_iam_role.fetched_from_aws",
                tags=stat_tags,
            )

        else:
            log_data["message"] = "Role fetched from DDB."
            stats.count("aws.fetch_iam_role.in_dynamo", tags=stat_tags)

            # Fix the TTL:
            iam_role.ttl = int(iam_role.ttl)

        log.debug(log_data)

        iam_role.policy = json.loads(iam_role.policy)
        return iam_role

    @classmethod
    async def create(
        cls, create_model: RoleCreationRequestModel, username: str, host: str
    ):
        results = await _create_iam_role(create_model, username, host)
        if results["role_created"] == "false":
            return None, results

        arn = f"arn:aws:iam::{create_model.account_id}:role/{create_model.role_name}"
        iam_role = await cls.get(create_model.account_id, host, arn, True)
        return iam_role, results

    @classmethod
    async def delete_role(
        cls, account_id: str, role_name: str, username: str, host: str
    ):
        arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        iam_role = await cls.get(account_id, host, arn)
        await _delete_iam_role(account_id, role_name, username, host)
        return await iam_role.delete()

    @classmethod
    async def clone(cls, clone_model: CloneRoleRequestModel, username, host):
        results = await _clone_iam_role(clone_model, username, host)
        if results["role_created"] == "false":
            return None, results

        arn = f"arn:aws:iam::{clone_model.dest_account_id}:role/{clone_model.dest_role_name}"
        iam_role = await cls.get(clone_model.dest_account_id, host, arn, True)
        return iam_role, results
