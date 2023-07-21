import asyncio
import random
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import contains_eager, joinedload

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.templates.models import IambicTemplate
from common.pg_core.utils import bulk_delete
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
)
from common.request_types.tasks import upsert_tenant_request_types
from common.request_types.utils import (
    get_tenant_change_type,
    list_tenant_change_types,
    list_tenant_request_types,
)
from qa import TENANT_SUMMARY
from qa.utils import generic_api_get_request

"""Example script
import asyncio


async def run_all_tests():
    from qa.request_types import (
        add_new_request_type,
        add_change_field,
        add_new_change_type_to_request_type,
        reinitialize_change_type,
        update_change_type,
        update_request_type,
        update_change_type_template,
        update_change_field,
        no_update_tenant_modified_change_type,
        no_update_tenant_modified_request_type,
        delete_request_type,
        delete_change_type,
        delete_change_field,
    )

    await add_new_request_type()
    await add_change_field()
    await add_new_change_type_to_request_type()
    await reinitialize_change_type()
    await update_change_type()
    await update_request_type()
    await update_change_type_template()
    await update_change_field()
    await no_update_tenant_modified_change_type()
    await no_update_tenant_modified_request_type()
    await delete_request_type()
    await delete_change_type()
    await delete_change_field()

asyncio.run(run_all_tests())
"""


async def get_iambic_template(template_type, resource_id):
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(IambicTemplate)
            .filter(IambicTemplate.template_type == template_type)
            .filter(IambicTemplate.resource_id == resource_id)
        )

        items = await session.execute(stmt)

        return items.scalars().unique().one_or_none()


async def get_request_type_by_id(request_type_id):
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(RequestType)
            .filter(RequestType.id == request_type_id)
            .outerjoin(ChangeType, ChangeType.request_type_id == RequestType.id)
        )

        items = await session.execute(
            stmt.options(
                contains_eager(RequestType.change_types).options(
                    joinedload(ChangeType.change_fields),
                    joinedload(ChangeType.change_template),
                )
            )
        )

        return items.scalars().unique().one_or_none()


async def get_change_type_by_id(change_type_id):
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(ChangeType)
            .filter(ChangeType.id == change_type_id)
            .outerjoin(ChangeField, ChangeField.change_type_id == ChangeType.id)
            .outerjoin(
                ChangeTypeTemplate, ChangeTypeTemplate.change_type_id == ChangeType.id
            )
        )

        items = await session.execute(
            stmt.options(
                contains_eager(ChangeType.change_fields),
                contains_eager(ChangeType.change_template),
            )
        )

        return items.scalars().unique().one_or_none()


async def hard_delete_request_type(request_type: RequestType):
    # Clear out change types, change fields, and change type templates
    async with ASYNC_PG_SESSION() as session:
        items = await session.execute(
            select(ChangeType).filter(ChangeType.request_type_id == request_type.id)
        )
        change_types = items.scalars().all()

    change_type_ids = [change_type.id for change_type in change_types]
    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = delete(ChangeTypeTemplate).where(
                ChangeTypeTemplate.change_type_id.in_(change_type_ids)
            )
            await session.execute(stmt)

            stmt = delete(ChangeField).where(
                ChangeField.change_type_id.in_(change_type_ids)
            )
            await session.execute(stmt)

    await bulk_delete(change_types)
    await bulk_delete([request_type])


async def hard_delete_change_type(change_type: ChangeType):
    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            stmt = delete(ChangeTypeTemplate).where(
                ChangeTypeTemplate.change_type_id == change_type.id
            )
            await session.execute(stmt)

            stmt = delete(ChangeField).where(
                ChangeField.change_type_id == change_type.id
            )
            await session.execute(stmt)

    await bulk_delete([change_type])


async def reset_request_type_tables():
    tenant = TENANT_SUMMARY.tenant
    request_types = await list_tenant_request_types(tenant.id, exclude_deleted=False)
    await asyncio.gather(
        *[hard_delete_request_type(req_type) for req_type in request_types]
    )

    await upsert_tenant_request_types(tenant.name)


async def add_new_request_type():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(tenant.id)
    init_count = len(tenant_request_types)

    # Addition by subtraction
    await hard_delete_request_type(tenant_request_types[-1])
    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert len(tenant_request_types) == init_count - 1

    await upsert_tenant_request_types(tenant.name)
    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert len(tenant_request_types) == init_count


async def update_request_type():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(tenant.id)
    rt = tenant_request_types[0]
    new_description = "This is an old but not really description"
    original_description = rt.description
    rt.description = new_description
    await rt.write()

    request_type = await get_request_type_by_id(rt.id)
    assert request_type.description == new_description

    await upsert_tenant_request_types(tenant.name)

    request_type = await get_request_type_by_id(rt.id)
    assert request_type.description == original_description


async def no_update_tenant_modified_request_type():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(tenant.id)
    rt = tenant_request_types[0]
    new_description = "This is an old but not really description"
    rt.description = new_description
    rt.updated_by = "SomeUser"
    rt.updated_at = datetime.utcnow()
    await rt.write()

    tenant_request_types = await list_tenant_request_types(tenant.id)

    assert any(trt.description == new_description for trt in tenant_request_types)

    await upsert_tenant_request_types(tenant.name)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert any(trt.description == new_description for trt in tenant_request_types)


async def delete_request_type():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(tenant.id)
    init_count = len(tenant_request_types)
    rt = tenant_request_types[0]
    new_name = "This is a non existent Noq resource type"
    rt.name = new_name
    await rt.write()

    updated_rt = await get_request_type_by_id(rt.id)
    assert updated_rt.name == new_name

    await upsert_tenant_request_types(tenant.name)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert len(tenant_request_types) == init_count

    updated_rt = await get_request_type_by_id(rt.id)
    assert updated_rt.deleted


async def reinitialize_change_type():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_change_types = await list_tenant_change_types(tenant.id)
    init_active_count = len(tenant_change_types)
    ct = random.choice(tenant_change_types)
    ct.deleted = True
    ct.deleted_at = datetime.utcnow()
    ct.template_types = []
    await ct.write()

    tenant_change_types = await list_tenant_change_types(tenant.id)
    assert len(tenant_change_types) == init_active_count - 1

    await upsert_tenant_request_types(tenant.name)

    tenant_change_types = await list_tenant_change_types(tenant.id)
    assert len(tenant_change_types) == init_active_count

    updated_rt = await get_tenant_change_type(tenant.id, ct.id)
    assert not updated_rt.deleted


async def add_new_change_type_to_request_type():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False
    )
    rt = tenant_request_types[0]
    removed_change_type = rt.change_types[-1]
    init_count = len(rt.change_types)
    assert init_count > 0

    # Addition by subtraction
    await hard_delete_change_type(removed_change_type)
    rt = await get_request_type_by_id(rt.id)
    # Verify change type was removed
    assert len(rt.change_types) == init_count - 1
    assert removed_change_type.name not in [ct.name for ct in rt.change_types]

    await upsert_tenant_request_types(tenant.name)
    rt = await get_request_type_by_id(rt.id)
    # Confirm change type was added back
    assert len(rt.change_types) == init_count
    assert removed_change_type.name in [ct.name for ct in rt.change_types]


async def update_change_type():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False
    )
    rt = tenant_request_types[0]
    updated_change_type = rt.change_types[-1]
    new_description = "This is the new description"
    original_description = updated_change_type.description
    updated_change_type.description = new_description
    await updated_change_type.write()

    rt = await get_request_type_by_id(rt.id)
    # Confirm description was properly applied
    assert new_description in [ct.description for ct in rt.change_types]

    await upsert_tenant_request_types(tenant.name)
    rt = await get_request_type_by_id(rt.id)
    # Verify it was updated because this is a Noq managed template
    assert original_description in [ct.description for ct in rt.change_types]


async def no_update_tenant_modified_change_type():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False
    )
    rt = tenant_request_types[0]
    updated_change_type = rt.change_types[-1]
    new_description = "This is the new description"
    updated_change_type.description = new_description
    updated_change_type.updated_at = datetime.utcnow()
    updated_change_type.updated_by = "TheTenant"
    await updated_change_type.write()

    rt = await get_request_type_by_id(rt.id)
    # Confirm description was properly applied
    assert new_description in [ct.description for ct in rt.change_types]

    await upsert_tenant_request_types(tenant.name)
    rt = await get_request_type_by_id(rt.id)
    # Verify it was not updated because this is a tenant managed template
    assert new_description in [ct.description for ct in rt.change_types]


async def update_change_type_template():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False
    )
    rt = tenant_request_types[0]
    updated_change_type = rt.change_types[-1]
    new_template = "This is the new template"
    original_template = updated_change_type.change_template.template
    assert new_template != original_template
    updated_change_type.change_template.template = new_template
    await updated_change_type.write()

    # Confirm template was properly applied
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert updated_change_type.change_template.template == new_template

    await upsert_tenant_request_types(tenant.name)
    # Verify it was updated because this is a Noq managed template
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert updated_change_type.change_template.template == original_template


async def delete_change_type():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False
    )
    rt = tenant_request_types[0]
    original_change_type_count = len(rt.change_types)
    updated_change_type = rt.change_types[-1]
    new_name = "This is the new name"
    updated_change_type.name = new_name
    await updated_change_type.write()

    rt = await get_request_type_by_id(rt.id)
    # Confirm name was properly applied
    assert new_name in [ct.name for ct in rt.change_types]

    await upsert_tenant_request_types(tenant.name)

    # Verify it was soft deleted because this is a Noq managed template
    rt = await get_request_type_by_id(rt.id)
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert updated_change_type.deleted
    assert len(rt.change_types) == original_change_type_count + 1


async def add_change_field():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False
    )
    rt = tenant_request_types[0]
    updated_change_type = rt.change_types[-1]
    original_change_field_count = len(updated_change_type.change_fields)
    removed_change_field = updated_change_type.change_fields[-1]
    await removed_change_field.delete()

    # Confirm change field was properly deleted
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert removed_change_field.field_key not in [
        cf.field_key for cf in updated_change_type.change_fields
    ]
    assert len(updated_change_type.change_fields) == original_change_field_count - 1

    await upsert_tenant_request_types(tenant.name)

    # Verify it was added back because this is a Noq managed template
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert removed_change_field.field_key in [
        cf.field_key for cf in updated_change_type.change_fields
    ]
    assert len(updated_change_type.change_fields) == original_change_field_count


async def update_change_field():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False
    )
    rt = tenant_request_types[0]
    updated_change_type = rt.change_types[-1]
    updated_change_field = updated_change_type.change_fields[-1]
    new_field_text = "This is the new field text"
    original_field_text = updated_change_field.field_text
    updated_change_field.field_text = new_field_text
    await updated_change_field.write()

    # Confirm change field was properly applied
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert original_field_text not in [
        cf.field_text for cf in updated_change_type.change_fields
    ]
    assert new_field_text in [cf.field_text for cf in updated_change_type.change_fields]

    await upsert_tenant_request_types(tenant.name)

    # Verify the change field text was updated because this is a Noq managed template
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert original_field_text in [
        cf.field_text for cf in updated_change_type.change_fields
    ]
    assert new_field_text not in [
        cf.field_text for cf in updated_change_type.change_fields
    ]


async def delete_change_field():
    tenant = TENANT_SUMMARY.tenant
    await reset_request_type_tables()

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False
    )
    rt = tenant_request_types[0]
    updated_change_type = rt.change_types[-1]
    original_change_field_count = len(updated_change_type.change_fields)
    new_change_field = ChangeField(
        change_type_id=updated_change_type.id,
        change_element=original_change_field_count,
        field_key="qa_test",
        field_type="TextBox",
        field_text="This is QA",
        description="This is the description",
        allow_none=True,
        allow_multiple=False,
    )
    assert new_change_field.field_key not in [
        cf.field_key for cf in updated_change_type.change_fields
    ]
    await new_change_field.write()

    # Confirm name was properly applied
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert new_change_field.field_key in [
        cf.field_key for cf in updated_change_type.change_fields
    ]
    assert len(updated_change_type.change_fields) == original_change_field_count + 1

    await upsert_tenant_request_types(tenant.name)

    # Verify it was soft deleted because this is a Noq managed template
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert new_change_field.field_key not in [
        cf.field_key for cf in updated_change_type.change_fields
    ]
    assert len(updated_change_type.change_fields) == original_change_field_count


async def api_list_providers():
    base_url = "v4/self-service/request-types"

    generic_api_get_request(base_url, provider="aws")


async def api_list_change_types(
    request_type_id: Optional[str] = None, iambic_templates_specified: bool = None
):
    if not request_type_id:
        tenant = TENANT_SUMMARY.tenant
        all_request_types = await list_tenant_request_types(tenant.id)
        request_type = random.choice(list(all_request_types))
        request_type_id = request_type.id

    base_url = "v4/self-service/request-types"
    change_type_url = f"{base_url}/{request_type_id}/change-types/"

    generic_api_get_request(
        change_type_url, iambic_templates_specified=iambic_templates_specified
    )


async def api_get_change_type(
    request_type_id: Optional[str] = None,
    change_type_id: Optional[str] = None,
):
    if change_type_id:
        assert request_type_id
    else:
        tenant = TENANT_SUMMARY.tenant
        all_request_types = await list_tenant_request_types(
            tenant.id, summary_only=False
        )
        if request_type_id:
            request_type = [rt for rt in all_request_types if rt.id == request_type_id]
            if not request_type:
                print(
                    f"Request type {request_type_id} not found. Using random request type."
                )
                request_type = random.choice(list(all_request_types))
        else:
            request_type = random.choice(list(all_request_types))

        request_type_id = request_type.id
        change_type = random.choice(request_type.change_types)
        change_type_id = change_type.id

    base_url = "v4/self-service/request-types"
    change_type_url = f"{base_url}/{request_type_id}/change-types/{change_type_id}"

    generic_api_get_request(change_type_url)


async def api_typeahead_list_groups(name: Optional[str] = None):
    request_params = {} if not name else {"name": name}
    generic_api_get_request("v4/self-service/typeahead/noq/groups", **request_params)


async def api_typeahead_list_users(email: Optional[str] = None):
    request_params = {} if not email else {"email": email}
    generic_api_get_request("v4/self-service/typeahead/noq/users", **request_params)


async def api_add_change_type():
    tenant = TENANT_SUMMARY.tenant
    request_types = await list_tenant_request_types(
        tenant.id, "aws", summary_only=False
    )
    request_type = [
        r
        for r in request_types
        if r.name == "Request access to AWS Identity Center (SSO) PermissionSet"
    ][0]

    # Select IAMbic Template with a certain resource ID
    iambic_template = await get_iambic_template(
        template_type="NOQ::AWS::IdentityCenter::PermissionSet",
        resource_id="AWSReadOnlyAccess",
    )

    assert iambic_template

    access_change_type = ChangeType(
        name="Readonly Access for CustomerA",
        description="Read Only Access to CustomerA's S3 buckets and Glue tables",
        change_fields=[],
        tenant_id=tenant.id,
        change_template=ChangeTypeTemplate(
            template="""
        {
            "users":["{{form.current_user}}"],
            "included_accounts": ["development"]
        }"""
        ),
        created_by="Noq",
        included_iambic_templates=[iambic_template],
    )

    request_type.change_types.append(access_change_type)
    await request_type.write()


if __name__ == "__main__":
    asyncio.run(TENANT_SUMMARY.setup())
    asyncio.run(api_add_change_type())
