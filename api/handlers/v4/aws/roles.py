# import itertools

import tornado.web

from common.aws.utils import ResourceAccountCache
from common.config import config
from common.handlers.base import BaseHandler
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.aws.cached_resources.iam import get_user_active_tra_roles_by_tag
from common.lib.filter import filter_data
from common.lib.plugins import get_plugin_by_name
from common.models import DataTableResponse

log = config.get_logger(__name__)


class RolesHandlerV4(BaseHandler):
    """Handler for /api/v4/aws/roles

    Api endpoint to list and filter roles
    """

    allowed_methods = ["POST"]

    async def post(self):
        """
        POST /api/v4/aws/roles
        """
        tenant = self.ctx.tenant
        body = tornado.escape.json_decode(self.request.body or "{}")

        group_mapping = get_plugin_by_name(
            config.get_tenant_specific_key(
                "plugins.group_mapping",
                tenant,
                "cmsaas_group_mapping",
            )
        )()

        self.eligible_roles = await group_mapping.get_eligible_roles(
            self.eligible_roles,
            self.user,
            self.groups,
            self.user_role_name,
            self.get_tenant_name(),
            console_only=True,
        )

        roles = []
        active_tra_roles = await get_user_active_tra_roles_by_tag(tenant, self.user)
        friendly_names = await get_account_id_to_name_mapping(tenant)
        for arn in self.eligible_roles:
            role_name = arn.split("/")[-1]
            account_id = await ResourceAccountCache.get(tenant, arn)
            account_name = friendly_names.get(account_id, "")
            if account_name and isinstance(account_name, list):
                account_name = account_name[0]
            if not account_name:
                continue
            formatted_account_name = config.get_tenant_specific_key(
                "role_select_page.formatted_account_name",
                tenant,
                "{account_name}",
            ).format(account_name=account_name, account_id=account_id)
            row = {
                "arn": arn,
                "account_name": formatted_account_name,
                "account_id": account_id,
                "role_name": f"[{role_name}](/policies/edit/{account_id}/iamrole/{role_name})",
                "redirect_uri": f"/role/{arn}",
                "inactive_tra": False,
            }

            if arn in active_tra_roles:
                row["content"] = "Sign-In (Temporary Access)"
                row["color"] = "red"

            roles.append(row)
        filtered_roles: DataTableResponse = await filter_data(roles, body)
        self.write(filtered_roles.dict())
        await self.finish()
