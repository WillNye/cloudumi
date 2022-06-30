from typing import Any, Dict, List

from common.config import config
from common.handlers.base import BaseAPIV2Handler
from common.lib.auth import can_admin_policies
from common.lib.defaults import PERMISSION_TEMPLATE_DEFAULTS, SELF_SERVICE_IAM_DEFAULTS


class SelfServiceConfigHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self):
        tenant = self.ctx.tenant
        admin_bypass_approval_enabled: bool = await can_admin_policies(
            self.user, self.groups, tenant, []
        )
        export_to_terraform_enabled: bool = config.get_tenant_specific_key(
            "export_to_terraform_enabled", tenant, False
        )
        self_service_iam_config: dict = config.get_tenant_specific_key(
            "self_service_iam", tenant, SELF_SERVICE_IAM_DEFAULTS
        )

        # Help message can be configured with Markdown for link handling
        help_message: str = config.get_tenant_specific_key(
            "self_service_iam_help_message", tenant
        )

        self.write(
            {
                "admin_bypass_approval_enabled": admin_bypass_approval_enabled,
                "export_to_terraform_enabled": export_to_terraform_enabled,
                "help_message": help_message,
                **self_service_iam_config,
            }
        )


class PermissionTemplatesHandler(BaseAPIV2Handler):
    allowed_methods = ["GET"]

    async def get(self):
        """
        Returns permission templates.

        Combines permission templates from dynamic configuration to the ones discovered in static configuration, with a
        priority to the templates defined in dynamic configuration.

        If no permission_templates are defined in static configuration, this function will substitute the static
        configuration templates with PERMISSION_TEMPLATE_DEFAULTS.
        """
        tenant = self.ctx.tenant
        permission_templates_dynamic_config: List[
            Dict[str, Any]
        ] = config.get_tenant_specific_key(
            "dynamic_config.permission_templates", tenant, []
        )

        permission_templates_config: List[
            Dict[str, Any]
        ] = config.get_tenant_specific_key(
            "permission_templates",
            tenant,
            PERMISSION_TEMPLATE_DEFAULTS,
        )

        seen = set()
        compiled_permission_templates = []
        for item in [
            *permission_templates_dynamic_config,
            *permission_templates_config,
        ]:
            if item["key"] in seen:
                continue
            compiled_permission_templates.append(item)
            seen.add(item["key"])

        self.write({"permission_templates": compiled_permission_templates})
