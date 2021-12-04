from typing import Dict

import ujson as json

from common.config import config
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.cloud_credential_authorization_mapping.models import (
    CredentialAuthzMappingGenerator,
    RoleAuthorizations,
    user_or_group,
)


class RoleTagAuthorizationMappingGenerator(CredentialAuthzMappingGenerator):
    """Generates an authorization mapping of groups -> roles based on IAM role tags."""

    async def generate_credential_authorization_mapping(
        self,
        authorization_mapping: Dict[user_or_group, RoleAuthorizations],
        host,
    ) -> Dict[user_or_group, RoleAuthorizations]:
        """This will list accounts that meet the account attribute search criteria."""
        # Retrieve roles
        cache_key = config.get_host_specific_key(
            f"site_configs.{host}.aws.iamroles_redis_key",
            host,
            f"{host}_IAM_ROLE_CACHE",
        )
        all_roles = await retrieve_json_data_from_redis_or_s3(
            redis_key=cache_key,
            redis_data_type="hash",
            s3_bucket=config.get_host_specific_key(
                f"site_configs.{host}.cache_iam_resources_across_accounts.all_roles_combined.s3.bucket",
                host,
            ),
            s3_key=config.get_host_specific_key(
                f"site_configs.{host}.cache_iam_resources_across_accounts.all_roles_combined.s3.file",
                host,
                "account_resource_cache/cache_all_roles_v1.json.gz",
            ),
            host=host,
            default={},
        )

        required_trust_policy_entity = config.get_host_specific_key(
            f"site_configs.{host}.cloud_credential_authorization_mapping.role_tags.required_trust_policy_entity",
            host,
        )

        for arn, role_entry_j in all_roles.items():
            role_entry = json.loads(role_entry_j)
            policy = json.loads(role_entry["policy"])
            tags = policy.get("Tags")

            if (
                required_trust_policy_entity
                and required_trust_policy_entity.lower()
                not in json.dumps(
                    policy["AssumeRolePolicyDocument"], escape_forward_slashes=False
                ).lower()
            ):
                continue

            for tag in tags:
                if tag["Key"] in config.get_host_specific_key(
                    f"site_configs.{host}.cloud_credential_authorization_mapping.role_tags.authorized_groups_tags",
                    host,
                    [],
                ):
                    splitted_groups = tag["Value"].split(":")
                    for group in splitted_groups:
                        if config.get_host_specific_key(
                            f"site_configs.{host}.auth.force_groups_lowercase",
                            host,
                            False,
                        ):
                            group = group.lower()
                        if not authorization_mapping.get(group):
                            authorization_mapping[group] = RoleAuthorizations.parse_obj(
                                {
                                    "authorized_roles": set(),
                                    "authorized_roles_cli_only": set(),
                                }
                            )
                        authorization_mapping[group].authorized_roles.add(arn)
                if tag["Key"] in config.get_host_specific_key(
                    f"site_configs.{host}.cloud_credential_authorization_mapping.role_tags.authorized_groups_cli_only_tags",
                    host,
                    [],
                ):
                    splitted_groups = tag["Value"].split(":")
                    for group in splitted_groups:
                        if config.get_host_specific_key(
                            f"site_configs.{host}.auth.force_groups_lowercase",
                            host,
                            False,
                        ):
                            group = group.lower()
                        if not authorization_mapping.get(group):
                            authorization_mapping[group] = RoleAuthorizations.parse_obj(
                                {
                                    "authorized_roles": set(),
                                    "authorized_roles_cli_only": set(),
                                }
                            )
                        authorization_mapping[group].authorized_roles_cli_only.add(arn)
        return authorization_mapping
