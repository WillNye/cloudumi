import sys
import time
from collections import defaultdict
from typing import Dict, List, Optional

import sentry_sdk
from pydantic.json import pydantic_encoder

from common.config import config
from common.lib.cache import (
    retrieve_json_data_from_redis_or_s3,
    store_json_results_in_redis_and_s3,
)
from common.lib.cloud_credential_authorization_mapping.dynamic_config import (
    DynamicConfigAuthorizationMappingGenerator,
)
from common.lib.cloud_credential_authorization_mapping.internal_plugin import (
    InternalPluginAuthorizationMappingGenerator,
)
from common.lib.cloud_credential_authorization_mapping.models import (
    RoleAuthorizations,
    RoleAuthorizationsDecoder,
    user_or_group,
)
from common.lib.singleton import Singleton

log = config.get_logger("cloudumi")


class CredentialAuthorizationMapping(metaclass=Singleton):
    def __init__(self) -> None:
        self._all_roles = defaultdict(list)
        self._all_roles_count = defaultdict(int)
        self._all_roles_last_update = defaultdict(int)
        self.authorization_mapping = defaultdict(dict)
        self.reverse_mapping = defaultdict(dict)

    async def retrieve_credential_authorization_mapping(
        self, host, max_age: Optional[int] = None
    ):
        """
        This function retrieves the credential authorization mapping. This is a mapping of users/groups to the IAM roles
        they are allowed to get credentials for. This is the authoritative mapping that ConsoleMe uses for access.

        :param max_age: Maximum allowable age of the credential authorization mapping. If the mapping is older than
        `max_age` seconds, this function will raise an exception and return an empty mapping.
        """
        if (
            not self.authorization_mapping.get(host, {}).get("authorization_mapping")
            or int(time.time())
            - self.authorization_mapping.get(host, {}).get("last_update", 0)
            > 60
        ):
            redis_topic = config.get_host_specific_key(
                "generate_and_store_credential_authorization_mapping.redis_key",
                host,
                f"{host}_CREDENTIAL_AUTHORIZATION_MAPPING_V1",
            )
            s3_bucket = config.get_host_specific_key(
                "generate_and_store_credential_authorization_mapping.s3.bucket",
                host,
                config.get(
                    "_global_.s3_cache_bucket",
                ),
            )
            s3_key = config.get_host_specific_key(
                "generate_and_store_credential_authorization_mapping.s3.file",
                host,
                "credential_authorization_mapping/credential_authorization_mapping_v1.json.gz",
            )
            try:
                self.authorization_mapping[host][
                    "authorization_mapping"
                ] = await retrieve_json_data_from_redis_or_s3(
                    redis_topic,
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                    json_object_hook=RoleAuthorizationsDecoder,
                    json_encoder=pydantic_encoder,
                    max_age=max_age,
                    host=host,
                    default={},
                )
                self.authorization_mapping[host]["last_update"] = int(time.time())
            except Exception as e:
                sentry_sdk.capture_exception()
                log.error(
                    {
                        "function": f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                        "error": f"Error loading cloud credential mapping. Returning empty mapping: {e}",
                        "host": host,
                    },
                    exc_info=True,
                )
                return {}
        return self.authorization_mapping[host]["authorization_mapping"]

    async def retrieve_reverse_authorization_mapping(
        self, host, max_age: Optional[int] = None
    ):
        """
        This function retrieves the inverse of the credential authorization mapping. This is a mapping of IAM roles
        to the users/groups that are allowed to access them. This mapping is used primarily for auditing.

        :param max_age: Maximum allowable age of the reverse credential authorization mapping. If the mapping is older
        than `max_age` seconds, this function will raise an exception and return an empty mapping.
        """
        if (
            not self.reverse_mapping.get(host, {}).get("reverse_mapping")
            or int(time.time())
            - self.reverse_mapping.get(host, {}).get("last_update", 0)
            > 60
        ):
            redis_topic = config.get_host_specific_key(
                "generate_and_store_reverse_authorization_mapping.redis_key",
                host,
                f"{host}_REVERSE_AUTHORIZATION_MAPPING_V1",
            )
            s3_bucket = config.get_host_specific_key(
                "generate_and_store_reverse_authorization_mapping.s3.bucket",
                host,
            )
            s3_key = config.get_host_specific_key(
                "generate_and_store_reverse_authorization_mapping.s3.file",
                host,
                "reverse_authorization_mapping/reverse_authorization_mapping_v1.json.gz",
            )
            try:
                self.reverse_mapping[host][
                    "reverse_mapping"
                ] = await retrieve_json_data_from_redis_or_s3(
                    redis_topic,
                    s3_bucket=s3_bucket,
                    s3_key=s3_key,
                    json_object_hook=RoleAuthorizationsDecoder,
                    json_encoder=pydantic_encoder,
                    max_age=max_age,
                    host=host,
                )
                self.reverse_mapping[host]["last_update"] = int(time.time())
            except Exception as e:
                sentry_sdk.capture_exception()
                log.error(
                    {
                        "function": f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                        "error": f"Error loading reverse credential mapping. Returning empty mapping: {e}",
                    },
                    exc_info=True,
                )
                return {}
        return self.reverse_mapping[host]["reverse_mapping"]

    async def retrieve_all_roles(self, host: str, max_age: Optional[int] = None):
        from common.aws.iam.role.models import IAMRole

        if (
            not self._all_roles[host]
            or int(time.time()) - self._all_roles_last_update.get(host, 0) > 600
        ):
            try:
                all_roles = await IAMRole.query(host, attributes_to_get=["arn"])
                all_roles = [role.arn for role in all_roles]
            except Exception as e:
                sentry_sdk.capture_exception()
                log.error(
                    {
                        "function": f"{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                        "error": f"Error loading IAM roles. Returning empty list: {e}",
                    },
                    exc_info=True,
                )
                return []
            self._all_roles[host] = all_roles
            self._all_roles_count[host] = len(self._all_roles)
            self._all_roles_last_update[host] = int(time.time())
        return self._all_roles[host]

    async def all_roles(self, host, paginate=False, page=None, count=None):
        return await self.retrieve_all_roles(host)

    async def number_roles(self, host) -> int:
        _ = await self.retrieve_all_roles(host)
        return self._all_roles_count.get(host, 0)

    async def determine_role_authorized_groups(
        self, account_id: str, role_name: str, host: str
    ):
        arn = f"arn:aws:iam::{account_id}:role/{role_name.lower()}"
        reverse_mapping = await self.retrieve_reverse_authorization_mapping(host)
        groups = reverse_mapping.get(arn, [])
        return set(groups)

    async def determine_users_authorized_roles(
        self, user, groups, host, include_cli=False
    ):
        if not groups:
            groups = []
        authorization_mapping = await self.retrieve_credential_authorization_mapping(
            host
        )
        authorized_roles = set()
        user_mapping = authorization_mapping.get(user, [])
        if user_mapping:
            authorized_roles.update(user_mapping.authorized_roles)
            if include_cli:
                authorized_roles.update(user_mapping.authorized_roles_cli_only)
        for group in groups:
            group_mapping = authorization_mapping.get(group, [])
            if group_mapping:
                authorized_roles.update(group_mapping.authorized_roles)
                if include_cli:
                    authorized_roles.update(group_mapping.authorized_roles_cli_only)
        return sorted(authorized_roles)


async def generate_and_store_reverse_authorization_mapping(
    authorization_mapping: Dict[user_or_group, RoleAuthorizations], host
) -> Dict[str, List[user_or_group]]:
    reverse_mapping = defaultdict(list)
    for identity, roles in authorization_mapping.items():
        for role in roles.authorized_roles:
            reverse_mapping[role.lower()].append(identity)
        for role in roles.authorized_roles_cli_only:
            reverse_mapping[role.lower()].append(identity)

    # Store in S3 and Redis
    redis_topic = config.get_host_specific_key(
        "generate_and_store_reverse_authorization_mapping.redis_key",
        host,
        f"{host}_REVERSE_AUTHORIZATION_MAPPING_V1",
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get_host_specific_key(
        "celery.active_region", host, config.region
    ) or config.get("environment") in ["dev", "test"]:
        s3_bucket = config.get_host_specific_key(
            "generate_and_store_credential_authorization_mapping.s3.bucket",
            host,
            config.get(
                "_global_.s3_cache_bucket",
            ),
        )
        s3_key = config.get_host_specific_key(
            "generate_and_store_reverse_authorization_mapping.s3.file",
            host,
            "reverse_authorization_mapping/reverse_authorization_mapping_v1.json.gz",
        )
    await store_json_results_in_redis_and_s3(
        reverse_mapping,
        redis_topic,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        json_encoder=pydantic_encoder,
        host=host,
    )
    return reverse_mapping


async def generate_and_store_credential_authorization_mapping(
    host,
) -> Dict[user_or_group, RoleAuthorizations]:
    from common.aws.iam.role.utils import get_authorized_group_map

    authorization_mapping: Dict[user_or_group, RoleAuthorizations] = {}

    if config.get_host_specific_key(
        "cloud_credential_authorization_mapping.role_tags.enabled",
        host,
        True,
    ):
        authorization_mapping = await get_authorized_group_map(
            authorization_mapping, host
        )

    if config.get_host_specific_key(
        "cloud_credential_authorization_mapping.dynamic_config.enabled",
        host,
        True,
    ):
        authorization_mapping = await DynamicConfigAuthorizationMappingGenerator().generate_credential_authorization_mapping(
            authorization_mapping, host
        )
    if config.get_host_specific_key(
        "cloud_credential_authorization_mapping.internal_plugin.enabled",
        host,
        False,
    ):
        authorization_mapping = await InternalPluginAuthorizationMappingGenerator().generate_credential_authorization_mapping(
            authorization_mapping, host
        )
    # Store in S3 and Redis
    redis_topic = config.get_host_specific_key(
        "generate_and_store_credential_authorization_mapping.redis_key",
        host,
        f"{host}_CREDENTIAL_AUTHORIZATION_MAPPING_V1",
    )
    s3_bucket = None
    s3_key = None
    if config.region == config.get_host_specific_key(
        "celery.active_region", host, config.region
    ) or config.get("_global_.environment") in [
        "dev",
        "test",
    ]:
        s3_bucket = config.get_host_specific_key(
            "generate_and_store_credential_authorization_mapping.s3.bucket",
            host,
            config.get(
                "_global_.s3_cache_bucket",
            ),
        )

        s3_key = config.get_host_specific_key(
            "generate_and_store_credential_authorization_mapping.s3.file",
            host,
            "credential_authorization_mapping/credential_authorization_mapping_v1.json.gz",
        )

    print(authorization_mapping)
    await store_json_results_in_redis_and_s3(
        authorization_mapping,
        redis_topic,
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        json_encoder=pydantic_encoder,
        host=host,
    )
    return authorization_mapping
