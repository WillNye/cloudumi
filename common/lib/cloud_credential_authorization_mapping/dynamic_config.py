import sys
from typing import Dict

from common.config import config
from common.lib.cloud_credential_authorization_mapping.models import (
    CredentialAuthzMappingGenerator,
    RoleAuthorizations,
    user_or_group,
)
from common.lib.redis import RedisHandler


class DynamicConfigAuthorizationMappingGenerator(CredentialAuthzMappingGenerator):
    async def generate_credential_authorization_mapping(
        self, authorization_mapping: Dict[user_or_group, RoleAuthorizations], host: str
    ) -> Dict[user_or_group, RoleAuthorizations]:
        """This will list accounts that meet the account attribute search criteria."""
        function = f"{__name__}.{sys._getframe().f_code.co_name}"
        log_data = {
            "function": function,
        }
        red = RedisHandler().redis_sync(host)
        if config.get("_global_.config.load_from_dynamo", True):
            config.CONFIG.load_dynamic_config_from_redis(log_data, host, red)
        group_mapping_configuration = config.get_host_specific_key(
            f"site_configs.{host}.dynamic_config.group_mapping", host
        )

        if not group_mapping_configuration:
            return authorization_mapping

        for group, role_mapping in group_mapping_configuration.items():
            if config.get_host_specific_key(
                f"site_configs.{host}.auth.force_groups_lowercase", host, False
            ):
                group = group.lower()
            if not authorization_mapping.get(group):
                authorization_mapping[group] = RoleAuthorizations.parse_obj(
                    {"authorized_roles": set(), "authorized_roles_cli_only": set()}
                )
            authorization_mapping[group].authorized_roles.update(
                role_mapping.get("roles", [])
            )
            authorization_mapping[group].authorized_roles_cli_only.update(
                role_mapping.get("cli_only_roles", [])
            )
        return authorization_mapping
