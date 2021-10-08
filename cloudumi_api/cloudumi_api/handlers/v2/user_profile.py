from typing import Dict

from cloudumi_common.config import config
from cloudumi_common.handlers.base import BaseAPIV1Handler
from cloudumi_common.lib.account_indexers import get_account_id_to_name_mapping
from cloudumi_common.lib.auth import (
    can_admin_policies,
    can_create_roles,
    can_delete_iam_principals,
    can_edit_dynamic_config,
)
from cloudumi_common.lib.generic import get_random_security_logo, is_in_group
from cloudumi_common.lib.plugins import get_plugin_by_name
from cloudumi_common.lib.v2.user_profile import get_custom_page_header

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger()


class UserProfileHandler(BaseAPIV1Handler):
    async def get(self):
        """
        Provide information about site configuration for the frontend
        :return:
        """
        host = self.ctx.host
        is_contractor = False  # TODO: Support other option
        site_config = {
            "consoleme_logo": await get_random_security_logo(host),
            "google_analytics": {
                "tracking_id": config.get_host_specific_key(
                    f"site_configs.{host}.google_analytics.tracking_id", host
                ),
                "options": config.get_host_specific_key(
                    f"site_configs.{host}.google_analytics.options", host, {}
                ),
            },
            "documentation_url": config.get_host_specific_key(
                f"site_configs.{host}.documentation_page",
                host,
                "https://hawkins.gitbook.io/consoleme/",
            ),
            "support_contact": config.get_host_specific_key(
                f"site_configs.{host}.support_contact", host
            ),
            "support_chat_url": config.get_host_specific_key(
                f"site_configs.{host}.support_chat_url",
                host,
                "https://discord.com/invite/nQVpNGGkYu",
            ),
            "security_logo": config.get_host_specific_key(
                f"site_configs.{host}.security_logo.image", host
            ),
            "security_url": config.get_host_specific_key(
                f"site_configs.{host}.security_logo.url", host
            ),
            # If site_config.landing_url is set, users will be redirected to the landing URL after authenticating
            # on the frontend.
            "landing_url": config.get_host_specific_key(
                f"site_configs.{host}.site_config.landing_url", host
            ),
            "notifications": {
                "enabled": config.get_host_specific_key(
                    f"site_configs.{host}.site_config.notifications.enabled", host
                ),
                "request_interval": config.get_host_specific_key(
                    f"site_configs.{host}.site_config.notifications.request_interval",
                    host,
                    60,
                ),
            },
        }

        custom_page_header: Dict[str, str] = await get_custom_page_header(
            self.user, self.groups, host
        )
        user_profile = {
            "site_config": site_config,
            "user": self.user,
            "can_logout": config.get_host_specific_key(
                f"site_configs.{host}.auth.set_auth_cookie", host, False
            ),
            "is_contractor": is_contractor,
            "employee_photo_url": "",  # TODO: Support custom employee URL
            "employee_info_url": "",  # TODO: Support custom employee info url
            "authorization": {
                "can_edit_policies": can_admin_policies(self.user, self.groups, host),
                "can_create_roles": can_create_roles(self.user, self.groups, host),
                "can_delete_iam_principals": can_delete_iam_principals(
                    self.user, self.groups, host
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
                "groups": {
                    "enabled": config.get_host_specific_key(
                        f"site_configs.{host}.headers.group_access.enabled", host, False
                    )
                },
                "users": {
                    "enabled": config.get_host_specific_key(
                        f"site_configs.{host}.headers.group_access.enabled", host, False
                    )
                },
                "policies": {
                    "enabled": config.get_host_specific_key(
                        f"site_configs.{host}.headers.policies.enabled", host, True
                    )
                    and not is_contractor
                },
                "self_service": {
                    "enabled": config.get_host_specific_key(
                        f"site_configs.{host}.enable_self_service", host, True
                    )
                    and not is_contractor
                },
                "api_health": {
                    "enabled": is_in_group(
                        self.user,
                        self.groups,
                        config.get_host_specific_key(
                            f"site_configs.{host}.groups.can_edit_health_alert",
                            host,
                            [],
                        ),
                    )
                },
                "audit": {
                    "enabled": is_in_group(
                        self.user,
                        self.groups,
                        config.get_host_specific_key(
                            f"site_configs.{host}.groups.can_audit", host, []
                        ),
                    )
                },
                "config": {
                    "enabled": can_edit_dynamic_config(self.user, self.groups, host)
                },
            },
            "accounts": await get_account_id_to_name_mapping(host),
        }

        self.set_header("Content-Type", "application/json")
        self.write(user_profile)
