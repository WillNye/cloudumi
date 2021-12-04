from typing import Dict

from common.config import config
from common.lib.cloud_credential_authorization_mapping.models import (
    CredentialAuthzMappingGenerator,
    RoleAuthorizations,
    user_or_group,
)
from common.lib.plugins import get_plugin_by_name


class InternalPluginAuthorizationMappingGenerator(CredentialAuthzMappingGenerator):
    async def generate_credential_authorization_mapping(
        self, authorization_mapping: Dict[user_or_group, RoleAuthorizations], host: str
    ) -> Dict[user_or_group, RoleAuthorizations]:
        """This will list accounts that meet the account attribute search criteria."""
        group_mapping = get_plugin_by_name(
            config.get_host_specific_key(
                f"site_configs.{host}.plugins.group_mapping",
                host,
                "cmsaas_group_mapping",
            )
        )()

        # Generate mapping from internal plugin
        authorization_mapping = (
            await group_mapping.generate_credential_authorization_mapping(
                authorization_mapping
            )
        )
        # Return mapping
        return authorization_mapping
