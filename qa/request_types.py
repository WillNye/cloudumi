import asyncio
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import contains_eager, joinedload

from common.config.globals import ASYNC_PG_SESSION
from common.pg_core.utils import bulk_delete
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
)
from common.request_types.tasks import upsert_tenant_request_types
from common.request_types.utils import list_tenant_request_types
from common.tenants.models import Tenant
from qa import TENANT_NAME


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

    await bulk_delete(change_types)
    await bulk_delete([request_type])


async def reset_request_type_tables(tenant: Tenant):
    request_types = await list_tenant_request_types(tenant.id, exclude_deleted=False)
    await asyncio.gather(
        *[hard_delete_request_type(req_type) for req_type in request_types]
    )

    await upsert_tenant_request_types(tenant.name)


async def add_new_request_type():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    init_count = len(tenant_request_types)

    # Addition by subtraction
    await hard_delete_request_type(tenant_request_types[-1])
    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert len(tenant_request_types) == init_count - 1

    await upsert_tenant_request_types(TENANT_NAME)
    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert len(tenant_request_types) == init_count


async def update_request_type():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    rt = tenant_request_types[0]
    new_description = "This is an old but not really description"
    original_description = rt.description
    rt.description = new_description
    await rt.write()

    request_type = await get_request_type_by_id(rt.id)
    assert request_type.description == new_description

    await upsert_tenant_request_types(TENANT_NAME)

    request_type = await get_request_type_by_id(rt.id)
    assert request_type.description == original_description


async def no_update_tenant_modified_request_type():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    rt = tenant_request_types[0]
    new_description = "This is an old but not really description"
    rt.description = new_description
    rt.updated_by = "SomeUser"
    rt.updated_at = datetime.utcnow()
    await rt.write()

    tenant_request_types = await list_tenant_request_types(tenant.id)

    assert any(trt.description == new_description for trt in tenant_request_types)

    await upsert_tenant_request_types(TENANT_NAME)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert any(trt.description == new_description for trt in tenant_request_types)


async def delete_request_type():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    init_count = len(tenant_request_types)
    rt = tenant_request_types[0]
    new_name = "This is a non existent Noq resource type"
    rt.name = new_name
    await rt.write()

    updated_rt = await get_request_type_by_id(rt.id)
    assert updated_rt.name == new_name

    await upsert_tenant_request_types(TENANT_NAME)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert len(tenant_request_types) == init_count

    updated_rt = await get_request_type_by_id(rt.id)
    assert updated_rt.deleted


async def reinitialize_request_type():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    init_active_count = len(tenant_request_types)
    rt = tenant_request_types[0]
    rt.deleted = True
    rt.deleted_at = datetime.utcnow()
    rt.supported_template_types = []
    await rt.write()

    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert len(tenant_request_types) == init_active_count - 1

    await upsert_tenant_request_types(TENANT_NAME)

    tenant_request_types = await list_tenant_request_types(tenant.id)
    assert len(tenant_request_types) == init_active_count

    updated_rt = await get_request_type_by_id(rt.id)
    assert not updated_rt.deleted


async def add_new_change_type_to_request_type():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False
    )
    rt = tenant_request_types[0]
    removed_change_type = rt.change_types[-1]
    init_count = len(rt.change_types)
    assert init_count > 0

    # Addition by subtraction
    await bulk_delete([removed_change_type])
    rt = await get_request_type_by_id(rt.id)
    # Verify change type was removed
    assert len(rt.change_types) == init_count - 1
    assert removed_change_type.name not in [ct.name for ct in rt.change_types]

    await upsert_tenant_request_types(TENANT_NAME)
    rt = await get_request_type_by_id(rt.id)
    # Confirm change type was added back
    assert len(rt.change_types) == init_count
    assert removed_change_type.name in [ct.name for ct in rt.change_types]


async def update_change_type():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

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

    await upsert_tenant_request_types(TENANT_NAME)
    rt = await get_request_type_by_id(rt.id)
    # Verify it was updated because this is a Noq managed template
    assert original_description in [ct.description for ct in rt.change_types]


async def no_update_tenant_modified_change_type():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

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

    await upsert_tenant_request_types(TENANT_NAME)
    rt = await get_request_type_by_id(rt.id)
    # Verify it was not updated because this is a tenant managed template
    assert new_description in [ct.description for ct in rt.change_types]


async def update_change_type_template():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

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

    rt = await get_request_type_by_id(rt.id)
    # Confirm template was properly applied
    assert new_template in [ct.change_template.template for ct in rt.change_types]
    assert original_template not in [
        ct.change_template.template for ct in rt.change_types
    ]

    await upsert_tenant_request_types(TENANT_NAME)
    rt = await get_request_type_by_id(rt.id)
    # Verify it was updated because this is a Noq managed template
    assert original_template in [ct.change_template.template for ct in rt.change_types]


async def delete_change_type():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

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

    await upsert_tenant_request_types(TENANT_NAME)

    # Verify it was soft deleted because this is a Noq managed template
    rt = await get_request_type_by_id(rt.id)
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert updated_change_type.deleted
    assert len(rt.change_types) == original_change_type_count + 1


async def add_change_field():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

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

    await upsert_tenant_request_types(TENANT_NAME)

    # Verify it was added back because this is a Noq managed template
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert removed_change_field.field_key in [
        cf.field_key for cf in updated_change_type.change_fields
    ]
    assert len(updated_change_type.change_fields) == original_change_field_count


async def update_change_field():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

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

    await upsert_tenant_request_types(TENANT_NAME)

    # Verify the change field text was updated because this is a Noq managed template
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert original_field_text in [
        cf.field_text for cf in updated_change_type.change_fields
    ]
    assert new_field_text not in [
        cf.field_text for cf in updated_change_type.change_fields
    ]


async def delete_change_field():
    tenant = await Tenant.get_by_name(TENANT_NAME)
    await reset_request_type_tables(tenant)

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

    await upsert_tenant_request_types(TENANT_NAME)

    # Verify it was soft deleted because this is a Noq managed template
    updated_change_type = await get_change_type_by_id(updated_change_type.id)
    assert new_change_field.field_key not in [
        cf.field_key for cf in updated_change_type.change_fields
    ]
    assert len(updated_change_type.change_fields) == original_change_field_count
