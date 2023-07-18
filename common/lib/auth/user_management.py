from common.group_memberships.models import upsert_and_remove_group_memberships
from common.groups.models import upsert_groups_by_name
from common.tenants.models import Tenant
from common.users.models import User


async def maybe_create_users_groups_in_database(
    db_tenant: Tenant | str,
    user: str,
    groups: list[str],
    description: str,
    managed_by: str,
):
    db_user = await User.get_by_email(db_tenant, user)
    new_groups = []
    if not db_user:
        if managed_by == "SSO":
            from common.celery_tasks.celery_tasks import app as celery_app

            celery_app.send_task(
                "common.celery_tasks.celery_tasks.cache_iambic_data_for_tenant",
                kwargs={
                    "tenant": db_tenant
                    if isinstance(db_tenant, str)
                    else db_tenant.name
                },
            )

        db_user = await User.create(
            db_tenant,
            user,
            user,
            None,
            managed_by=managed_by,
            description=description,
        )
    if groups:
        res = await upsert_groups_by_name(
            db_tenant,
            groups,
            description=description,
            managed_by=managed_by,
        )
        all_groups = res.get("all_groups")
        new_groups = res.get("new_groups")
        await upsert_and_remove_group_memberships([db_user], all_groups)
    if new_groups:
        from common.celery_tasks.celery_tasks import app as celery_app

        celery_app.send_task(
            "common.celery_tasks.celery_tasks.run_full_iambic_sync_for_tenant",
            kwargs={"tenant": db_tenant.name},
        )
