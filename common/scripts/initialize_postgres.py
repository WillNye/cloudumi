import os

os.environ.setdefault(
    "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
)
os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")

from common.config.globals import ASYNC_PG_ENGINE  # noqa: E402
from common.github.models import GitHubInstall, GitHubOAuthState  # noqa: F401,E402
from common.group_memberships.models import GroupMembership  # noqa: E402
from common.groups.models import Group  # noqa: E402
from common.tenants.models import Tenant  # noqa: E402
from common.users.models import User  # noqa: E402


async def rebuild_tables():
    tenants = [
        {
            "name": "localhost",
            "user": "user@noq.dev",
            "groups": ["noq_admins@noq.dev", "engineering@noq.dev"],
        },
        {
            "name": "cloudumidev_com",
            "user": "admin_user@noq.dev",
            "groups": ["noq_admins@noq.dev"],
        },
        {
            "name": "cloudumisamldev_com",
            "user": "admin_user@noq.dev",
            "groups": ["noq_admins@noq.dev"],
        },
    ]
    async with ASYNC_PG_ENGINE.begin():
        for tenant_info in tenants:
            existing_tenant = await Tenant.get_by_name(tenant_info["name"])
            if not existing_tenant:
                tenant = await Tenant.create(
                    name=tenant_info["name"],
                    organization_id=tenant_info["name"],
                )
            else:
                tenant = existing_tenant

            existing_user = await User.get_by_email(tenant, tenant_info["user"])
            if not existing_user:
                user = await User.create(
                    tenant,
                    tenant_info["user"],
                    tenant_info["user"],
                    "Password!1",
                    email_verified=True,
                    managed_by="MANUAL",
                )
            else:
                user = existing_user

            for group_name in tenant_info["groups"]:
                existing_group = await Group.get_by_email(tenant, group_name)
                if not existing_group:
                    group = await Group.create(
                        tenant=tenant,
                        name=group_name,
                        email=group_name,
                        description="test",
                        managed_by="MANUAL",
                    )
                else:
                    group = existing_group

                existing_membership = await GroupMembership.get(user=user, group=group)
                if not existing_membership:
                    await GroupMembership.create(user, group)
