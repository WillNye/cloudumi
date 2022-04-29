"""Group mapping plugin."""
import sys
from typing import List

import sentry_sdk

from common.config import config
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.cloud_credential_authorization_mapping import (
    CredentialAuthorizationMapping,
)
from common.lib.plugins import get_plugin_by_name

log = config.get_logger("cloudumi")
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
credential_authz_mapping = CredentialAuthorizationMapping()

# TODO: Docstrings should provide examples of the data that needs to be returned


class GroupMapping:
    """Group mapping handles mapping groups to eligible roles and accounts."""

    def __init__(self):
        pass

    async def get_eligible_roles(
        self,
        roles: list[str],
        username: str,
        groups: list,
        user_role: str,
        host: str,
        console_only: bool,
        **kwargs,
    ) -> list:
        """Get eligible roles for user."""
        # Legacy cruft, we should rename the parameter here.
        include_cli: bool = not console_only

        roles.extend(
            await credential_authz_mapping.determine_users_authorized_roles(
                username, groups, host, include_cli
            )
        )

        return list(set(roles))

    @staticmethod
    async def filter_eligible_roles(query: str, obj: object) -> List:
        selected_roles: List = []
        for r in obj.eligible_roles:
            if query.lower() == r.lower():
                # Exact match. Only return the specific role
                return [r]
            if query.lower() in r.lower():
                selected_roles.append(r)
        return list(set(selected_roles))

    async def generate_credential_authorization_mapping(self, authorization_mapping):
        # Override this with company-specific logic
        return authorization_mapping

    async def get_eligible_accounts(self, request_object):
        """Get eligible accounts for user."""
        host = request_object.get_host_name()
        role_arns = request_object.eligible_roles
        stats.count("get_eligible_accounts")
        account_ids = {}

        friendly_names = await get_account_id_to_name_mapping(host)
        for r in role_arns:
            try:
                account_id = r.split(":")[4]
                account_friendlyname = friendly_names.get(account_id, "")
                if account_friendlyname and isinstance(account_friendlyname, list):
                    account_ids[account_id] = account_friendlyname[0]
                elif account_friendlyname and isinstance(account_friendlyname, str):
                    account_ids[account_id] = account_friendlyname
            except Exception as e:
                log.error(
                    {
                        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                        "message": "Unable to parse role ARN",
                        "role": r,
                        "error": str(e),
                    }
                )
                sentry_sdk.capture_exception()
        return account_ids

    async def get_account_mappings(self) -> dict:
        """Get a dictionary with all of the account mappings (friendly names -> ID and ID -> names)."""
        return {}

    async def get_secondary_approvers(self, group, host, return_default=False):
        return config.get_host_specific_key("access_requests.default_approver", host)

    def get_account_names_to_ids(self, force_refresh: bool = False) -> dict:
        """Get account name to id mapping"""
        stats.count("get_account_names_to_ids")
        return {}

    def get_account_ids_to_names(self, force_refresh: bool = False) -> str:
        """Get account id to name mapping"""
        stats.count("get_account_ids_to_names")
        return {}

    async def get_max_cert_age_for_role(self, role_name: str):
        """Retrieve the maximum allowed certificate age allowable to retrieve a particular
        role. 30 will be returned if there is no max age defined.
        """
        return 360

    async def get_all_account_data(self):
        return {}

    async def get_all_accounts(self):
        """Get all account details"""
        return {}

    async def get_all_user_groups(self, user, groups):
        return []

    def is_role_valid(self, entry):
        return True


def init():
    """Initialize group_mapping plugin."""
    return GroupMapping()
