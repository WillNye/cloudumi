from typing import Dict

from common.config import config
from common.handlers.base import BaseAPIV1Handler
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.auth import (
    can_admin_policies,
    can_create_roles,
    can_delete_iam_principals,
    can_edit_dynamic_config,
    is_tenant_admin,
)
from common.lib.generic import get_random_security_logo, is_in_group
from common.lib.plugins import get_plugin_by_name
from common.lib.v2.user_profile import get_custom_page_header

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class UserProfileHandler(BaseAPIV1Handler):
    async def get(self):
        """
        Provide information about site configuration for the frontend
        :return:
        """
        tenant = self.ctx.tenant
        is_contractor = False  # TODO: Support other option

        landing_url = config.get_tenant_specific_key("landing_url", tenant)
        if (
            config.get_tenant_specific_key("hub_account", tenant) is None
        ) and is_tenant_admin(self.user, self.groups, tenant):
            landing_url = "/onboarding"

        site_config = {
            "consoleme_logo": await get_random_security_logo(tenant),
            "google_analytics": {
                "tracking_id": config.get("_global_.google_analytics.tracking_id"),
                "options": config.get("_global_.google_analytics.options", {}),
            },
            "documentation_url": config.get_tenant_specific_key(
                "documentation_page",
                tenant,
                "/docs",
            ),
            "support_contact": config.get_tenant_specific_key(
                "support_contact", tenant
            ),
            "support_chat_url": config.get_tenant_specific_key(
                "support_chat_url",
                tenant,
                "https://communityinviter.com/apps/noqcommunity/noq",
            ),
            "security_logo": None,
            "favicon": None,
            "security_url": None,
            # If site_config.landing_url is set, users will be redirected to the landing URL after authenticating
            # on the frontend.
            "landing_url": landing_url,
            "notifications": {
                "enabled": config.get_tenant_specific_key(
                    "notifications.enabled", tenant
                ),
                "request_interval": config.get_tenant_specific_key(
                    "notifications.request_interval",
                    tenant,
                    60,
                ),
            },
            "temp_policy_support": config.get_tenant_specific_key(
                "policies.temp_policy_support", tenant, True
            ),
        }

        custom_page_header: Dict[str, str] = await get_custom_page_header(
            self.user, self.groups, tenant
        )

        user_profile = {
            "site_config": site_config,
            "user": self.user,
            "can_logout": config.get("_global_.auth.set_auth_cookie", True),
            "is_contractor": is_contractor,
            "employee_photo_url": "",  # TODO: Support custom employee URL
            "employee_info_url": "",  # TODO: Support custom employee info url
            "authorization": {
                "can_edit_policies": await can_admin_policies(
                    self.user, self.groups, tenant, []
                ),
                "can_create_roles": can_create_roles(self.user, self.groups, tenant),
                "can_delete_iam_principals": can_delete_iam_principals(
                    self.user, self.groups, tenant
                ),
            },
            "pages": {
                "header": {
                    "custom_header_message_title": custom_page_header.get(
                        "custom_header_message_title", ""
                    ),
                    "custom_header_message_text": custom_page_header.get(
                        "custom_header_message_text", ""
                    ),
                    "custom_header_message_route": custom_page_header.get(
                        "custom_header_message_route", ""
                    ),
                },
                "role_login": {
                    "enabled": config.get_tenant_specific_key(
                        "headers.role_login.enabled", tenant, True
                    )
                },
                "groups": {
                    "enabled": config.get_tenant_specific_key(
                        "headers.group_access.enabled", tenant, False
                    )
                },
                "identity": {
                    "enabled": config.get_tenant_specific_key(
                        "headers.identity.enabled", tenant, False
                    )
                },
                "users": {
                    "enabled": config.get_tenant_specific_key(
                        "headers.group_access.enabled", tenant, False
                    )
                },
                "policies": {
                    "enabled": config.get_tenant_specific_key(
                        "headers.policies.enabled", tenant, True
                    )
                    and not is_contractor
                },
                "self_service": {
                    "enabled": config.get_tenant_specific_key(
                        "enable_self_service", tenant, True
                    )
                    and not is_contractor
                },
                "api_health": {
                    "enabled": is_in_group(
                        self.user,
                        self.groups,
                        config.get_tenant_specific_key(
                            "groups.can_edit_health_alert",
                            tenant,
                            [],
                        ),
                    )
                },
                "audit": {
                    "enabled": is_in_group(
                        self.user,
                        self.groups,
                        config.get_tenant_specific_key("groups.can_audit", tenant, []),
                    )
                },
                "config": {
                    "enabled": can_edit_dynamic_config(self.user, self.groups, tenant)
                },
            },
            "accounts": await get_account_id_to_name_mapping(tenant),
        }

        self.set_header("Content-Type", "application/json")
        self.write(user_profile)
