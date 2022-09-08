import json
import sys
from datetime import datetime
from typing import Dict, Iterable, Optional, Sequence, Type

from botocore.exceptions import ClientError
from pynamodax.attributes import ListAttribute, NumberAttribute, UnicodeAttribute
from pynamodax.exceptions import DoesNotExist
from pynamodax.expressions.condition import Condition
from pynamodax.models import _T, _KeyType
from pynamodax.pagination import ResultIterator
from pynamodax.settings import OperationSettings

from common.aws.base_model import TagMap
from common.aws.iam.role.utils import (
    _clone_iam_role,
    _create_iam_role,
    _delete_iam_role,
    _get_iam_role_async,
    _get_iam_role_sync,
)
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
from common.lib.terraform.transformers.IAMRoleTransformer import IAMRoleTransformer
from common.models import CloneRoleRequestModel, RoleCreationRequestModel, SpokeAccount

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "fluent_bit"))()
log = get_logger(__name__)


class IAMRole(NoqModel):
    class Meta:
        host = dynamodb_host
        table_name = get_dynamo_table_name("iamroles_multitenant")
        dax_write_endpoints = dax_endpoints
        dax_read_endpoints = dax_endpoints
        fallback_to_dynamodb = True
        region = config.region

    tenant = UnicodeAttribute(hash_key=True)
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
    last_updated = NumberAttribute()

    @property
    def role_id(self):
        return f"{self.arn}||{self.tenant}"

    @property
    def assume_role_policy_document(self):
        return self.policy_dict.get("AssumeRolePolicyDocument", {})

    @property
    def policy_dict(self) -> dict:
        if getattr(self, "_policy_dict", None) is None:
            if not self.policy:
                self._policy_dict = {}
            elif isinstance(self.policy, str):
                self._policy_dict = json.dumps(self.policy)
            else:
                self._policy_dict = self.policy

        return self._policy_dict

    @property
    def terraform(self) -> str:
        if not self.policy_dict:
            return ""

        try:
            iam_role_transformer = IAMRoleTransformer(self.policy_dict)
            return iam_role_transformer.generate_hcl2_code(self.policy_dict)
        except Exception as err:
            log.warning(
                {
                    "message": "Unable to generate Terraform",
                    "IAMRole": self.role_id,
                    "error": str(err),
                }
            )
            return ""

    def _normalize_object(self):
        if self.policy and isinstance(self.policy, str):
            self.policy = json.loads(self.policy)

    def dict(self) -> dict:
        as_dict = super(IAMRole, self).dict()
        as_dict["terraform"] = self.terraform
        return as_dict

    @classmethod
    async def get(
        cls,
        tenant: str,
        account_id: str,
        arn: str,
        force_refresh: bool = False,
        run_sync: bool = False,
    ) -> "IAMRole":
        from common.aws.iam.utils import _cloudaux_to_aws
        from common.lib.aws.utils import get_aws_principal_owner

        stat_tags = {
            "account_id": account_id,
            "role_arn": arn,
            "tenant": tenant,
        }
        log_data: dict = {
            "function": f"{sys._getframe().f_code.co_name}",
            "role_arn": arn,
            "account_id": account_id,
            "force_refresh": force_refresh,
            "tenant": tenant,
        }
        iam_role = None
        entity_id = f"{arn}||{tenant}"

        if not force_refresh:
            try:
                iam_role: IAMRole = await super(IAMRole, cls).get(tenant, entity_id)
            except DoesNotExist:
                log_data["message"] = "Role is missing in DDB. Going out to AWS."
                stats.count("aws.fetch_iam_role.missing_dynamo", tags=stat_tags)

        if not iam_role:
            if force_refresh:
                log_data["message"] = "Force refresh is enabled. Going out to AWS."
                stats.count("aws.fetch_iam_role.force_refresh", tags=stat_tags)
            log.debug(log_data)

            try:
                role_name = arn.split("/")[-1]
                conn = {
                    "account_number": account_id,
                    "assume_role": ModelAdapter(SpokeAccount)
                    .load_config("spoke_accounts", tenant)
                    .with_query({"account_id": account_id})
                    .first.name,
                    "region": config.region,
                    "client_kwargs": config.get_tenant_specific_key(
                        "boto3.client_kwargs", tenant, {}
                    ),
                }
                if run_sync:
                    role = _get_iam_role_sync(account_id, role_name, conn, tenant)
                else:
                    role = await _get_iam_role_async(
                        account_id, role_name, conn, tenant
                    )

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
                tenant=tenant,
                name=role.get("RoleName"),
                resourceId=role.get("RoleId"),
                accountId=account_id,
                tags=[TagMap(**tag) for tag in role.get("Tags", [])],
                policy=cls().dump_json_attr(role),
                permissions_boundary=role.get("PermissionsBoundary", {}),
                owner=get_aws_principal_owner(role, tenant),
                last_updated=last_updated,
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

        log.debug(log_data)

        iam_role._normalize_object()
        return iam_role

    @classmethod
    async def create(
        cls, tenant: str, username: str, create_model: RoleCreationRequestModel
    ):
        results = await _create_iam_role(create_model, username, tenant)
        if results["role_created"] == "false":
            return None, results

        arn = f"arn:aws:iam::{create_model.account_id}:role/{create_model.role_name}"
        iam_role = await cls.get(tenant, create_model.account_id, arn, True)
        return iam_role, results

    @classmethod
    async def delete_role(
        cls, tenant: str, account_id: str, role_name: str, username: str
    ):
        arn = f"arn:aws:iam::{account_id}:role/{role_name}"
        iam_role = await cls.get(tenant, account_id, arn)
        await _delete_iam_role(account_id, role_name, username, tenant)
        return await iam_role.delete()

    @classmethod
    async def clone(cls, tenant, username, clone_model: CloneRoleRequestModel):
        results = await _clone_iam_role(clone_model, username, tenant)
        if results["role_created"] == "false":
            return None, results

        arn = f"arn:aws:iam::{clone_model.dest_account_id}:role/{clone_model.dest_role_name}"
        iam_role = await cls.get(tenant, clone_model.dest_account_id, arn, True)
        return iam_role, results

    @classmethod
    async def _batch_write_role(
        cls, tenant: str, account_id: str, filtered_iam_roles: list[dict]
    ):
        from common.lib.aws.utils import get_aws_principal_owner

        # Don't use this. It doesn't work but the implementation looks good.
        # When this is stable we'll replace existing logic which just calls save for each role

        last_updated: int = int((datetime.utcnow()).timestamp())

        with cls.batch_write() as batch:
            for role in filtered_iam_roles:
                entity_id = f"{role.get('Arn')}||{tenant}"
                batch.save(
                    cls(
                        arn=role.get("Arn"),
                        entity_id=entity_id,
                        tenant=tenant,
                        name=role.get("RoleName"),
                        resourceId=role.get("RoleId"),
                        accountId=account_id,
                        tags=[TagMap(**tag) for tag in role.get("Tags", [])],
                        policy=cls().dump_json_attr(role),
                        permissions_boundary=role.get("PermissionsBoundary", {}),
                        owner=get_aws_principal_owner(role, tenant),
                        last_updated=last_updated,
                    )
                )

    @classmethod
    async def sync_account_roles(
        cls, tenant: str, account_id: str, iam_roles: list[dict]
    ) -> bool:
        from common.lib.aws.utils import allowed_to_sync_role, get_aws_principal_owner

        aws = get_plugin_by_name(
            config.get_tenant_specific_key("plugins.aws", tenant, "cmsaas_aws")
        )()
        last_updated: int = int((datetime.utcnow()).timestamp())
        filtered_iam_roles = []
        cache_refresh_required = False

        # Remove deleted roles from cache
        iam_role_arns = [role.get("Arn") for role in iam_roles]
        cached_roles: list[IAMRole] = await cls.query(
            tenant, filter_condition=IAMRole.accountId == account_id
        )
        for cached_role in cached_roles:
            if cached_role.arn not in iam_role_arns:
                cache_refresh_required = True
                await cached_role.delete()

        for role in iam_roles:
            arn = role.get("Arn", "")
            tags = role.get("Tags", [])
            if allowed_to_sync_role(arn, tags, tenant):
                filtered_iam_roles.append(role)

        for role in filtered_iam_roles:
            entity_id = f"{role.get('Arn')}||{tenant}"
            await cls(
                arn=role.get("Arn"),
                entity_id=entity_id,
                tenant=tenant,
                name=role.get("RoleName"),
                resourceId=role.get("RoleId"),
                accountId=account_id,
                tags=[TagMap(**tag) for tag in role.get("Tags", [])],
                policy=cls().dump_json_attr(role),
                permissions_boundary=role.get("PermissionsBoundary", {}),
                owner=get_aws_principal_owner(role, tenant),
                last_updated=last_updated,
            ).save()

        for role in iam_roles:
            # Run internal function on role. This can be used to inspect roles, add managed policies, or other actions
            aws.handle_detected_role(role)

        return cache_refresh_required

    @classmethod
    async def _parse_results(cls, results: ResultIterator[_T]) -> list:
        iam_roles = []
        for iam_role in results:
            iam_role._normalize_object()
            iam_roles.append(iam_role)

        return iam_roles

    @classmethod
    async def scan(
        cls: Type[_T],
        filter_condition: Optional[Condition] = None,
        segment: Optional[int] = None,
        total_segments: Optional[int] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Dict[str, any]]] = None,
        page_size: Optional[int] = None,
        consistent_read: Optional[bool] = None,
        index_name: Optional[str] = None,
        rate_limit: Optional[float] = None,
        attributes_to_get: Optional[Sequence[str]] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> list:
        results = await super(IAMRole, cls).scan(
            filter_condition,
            segment,
            total_segments,
            limit,
            last_evaluated_key,
            page_size,
            consistent_read,
            index_name,
            rate_limit,
            attributes_to_get,
            settings,
        )
        return await cls._parse_results(results)

    @classmethod
    async def query(
        cls: Type[_T],
        hash_key: _KeyType,
        range_key_condition: Optional[Condition] = None,
        filter_condition: Optional[Condition] = None,
        consistent_read: bool = False,
        index_name: Optional[str] = None,
        scan_index_forward: Optional[bool] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Dict[str, any]]] = None,
        attributes_to_get: Optional[Iterable[str]] = None,
        page_size: Optional[int] = None,
        rate_limit: Optional[float] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> list:
        results = await super(IAMRole, cls).query(
            hash_key,
            range_key_condition,
            filter_condition,
            consistent_read,
            index_name,
            scan_index_forward,
            limit,
            last_evaluated_key,
            attributes_to_get,
            page_size,
            rate_limit,
            settings,
        )
        return await cls._parse_results(results)
