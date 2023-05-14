import os

os.environ.setdefault(
    "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
)
os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")

from common.config.globals import ASYNC_PG_ENGINE  # noqa: E402
from common.group_memberships.models import GroupMembership  # noqa: E402
from common.groups.models import Group  # noqa: E402
from common.tenants.models import Tenant  # noqa: E402
from common.users.models import User  # noqa: E402


async def rebuild_tables():
    async with ASYNC_PG_ENGINE.begin():
        tenant = await Tenant.create(
            name="localhost",
            organization_id="localhost",
        )
        tenant_cloudumidev = await Tenant.create(
            name="cloudumidev_com",
            organization_id="cloudumidev_com",
        )
        tenant_cloudumisamldev = await Tenant.create(
            name="cloudumisamldev_com",
            organization_id="cloudumisamldev_com",
        )
        user = await User.create(
            tenant,
            "admin_user@noq.dev",
            "admin_user@noq.dev",
            "Password!1",
            email_verified=True,
            managed_by="MANUAL",
        )
        group = await Group.create(
            tenant=tenant,
            name="noq_admins",
            email="noq_admins@noq.dev",
            description="test",
            managed_by="MANUAL",
        )
        await GroupMembership.create(user, group)
        user2 = await User.create(
            tenant_cloudumidev,
            "admin_user@noq.dev",
            "admin_user@noq.dev",
            "Password!1",
            email_verified=True,
        )
        group2 = await Group.create(
            tenant=tenant_cloudumidev,
            name="noq_admins",
            email="noq_admins@noq.dev",
            description="test",
        )
        await GroupMembership.create(user2, group2)

        user3 = await User.create(
            tenant_cloudumisamldev,
            "admin_user@noq.dev",
            "admin_user@noq.dev",
            "Password!1",
            email_verified=True,
        )
        group3 = await Group.create(
            tenant=tenant_cloudumisamldev,
            name="noq_admins",
            email="noq_admins@noq.dev",
            description="test",
        )
        await GroupMembership.create(user3, group3)
