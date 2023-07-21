import asyncio
from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from itertools import chain

from sqlalchemy import select

from common.config import config
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.templates.models import IambicTemplate
from common.pg_core.utils import bulk_add
from common.request_types.defaults.aws import get_default_aws_request_types
from common.request_types.defaults.azure_ad import get_default_azure_ad_request_types
from common.request_types.defaults.google_workspace import (
    get_default_google_workspace_request_types,
)
from common.request_types.utils import list_tenant_request_types
from common.tenants.models import Tenant

log = config.get_logger(__name__)


async def upsert_tenant_request_types(tenant_name: str):
    """
    Consume tenant name

    Checks that tenant has all supported request types
    Checks that existing supported request types are not out of date
    Conditionally reinitialize request types
        This happens when a request type previously had no supported template types for the tenant
            But now there are
    Conditionally delete request types
        This happens when
            A request type no longer has any supported template types for the tenant
            or
            A Noq managed request type is no longer supported
                This check is ignored if the Noq managed template was updated by the tenant putting it into a "detached" state
    Conditionally delete change types, fields, and templates
        This happens when
            A Noq managed request type is no longer supported
                This check is ignored if the Noq managed template was updated by the tenant putting it into a "detached" state
    Checks that each request type has all supported changes
    Checks that each request types change is not out of date
        This includes
            change type attributes
            change fields
            change type templates
    """
    tenant = await Tenant.get_by_name(tenant_name)
    if not tenant:
        return
    updated_at = datetime.utcnow()

    # Ensure tenant.supported_tenant_types is up to date
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(IambicTemplate)
            .filter(IambicTemplate.tenant_id == tenant.id)
            .distinct(IambicTemplate.template_type)
        )  # noqa: E712
        results = await session.execute(stmt)
        tenant_template_types = sorted(
            [t.template_type for t in results.scalars().all()]
        )

    if not tenant.supported_template_types or tenant_template_types != sorted(
        tenant.supported_template_types
    ):
        tenant.supported_template_types = tenant_template_types
        await tenant.write()

        if not tenant.supported_template_types:
            log.error(
                {
                    "message": "No template types supported for tenant",
                    "tenant": tenant.name,
                }
            )
            return

    tenant_request_types = await list_tenant_request_types(
        tenant.id, summary_only=False, exclude_deleted=False
    )
    tenant_request_type_map = {rt.name: rt for rt in tenant_request_types}
    tenant_request_type_change_map = defaultdict(dict)
    for request_type in tenant_request_types:
        for change_type in request_type.change_types:
            change_type.tenant_id = tenant.id
            tenant_request_type_change_map[request_type.name][
                change_type.name
            ] = change_type

    default_request_types = await get_default_aws_request_types()
    default_request_types.extend(
        await asyncio.gather(get_default_google_workspace_request_types())
    )
    default_request_types.extend(
        await asyncio.gather(get_default_azure_ad_request_types())
    )
    default_request_types = list(chain.from_iterable(default_request_types))
    default_request_type_map = {rt.name: rt for rt in default_request_types}
    default_request_type_change_map = defaultdict(dict)
    for request_type in default_request_types:
        for default_change_type in request_type.change_types:
            change_type = deepcopy(default_change_type)
            change_type.template_types = [
                tt for tt in change_type.supported_template_types if tt in tenant_template_types
            ]
            if not change_type.template_types:
                change_type.deleted = True
            change_type.tenant_id = tenant.id
            default_request_type_change_map[request_type.name][
                change_type.name
            ] = change_type

    if not tenant_request_types:
        new_request_types = []
        for request_type in default_request_types:
            request_type.tenant_id = tenant.id

        await bulk_add(new_request_types)
        return

    # Update existing request type and change types
    for request_type in tenant_request_types:
        write_obj = False
        default_request_type = default_request_type_map.get(request_type.name)

        if request_type.updated_by in ["Noq", None]:
            # A user managed request type can still have Noq managed change types
            if not default_request_type:
                # This request type was managed and removed by Noq so remove it from the tenant
                await request_type.delete()
                continue

            for attr in [
                "description",
            ]:
                if getattr(request_type, attr) != getattr(default_request_type, attr):
                    setattr(request_type, attr, getattr(default_request_type, attr))
                    request_type.updated_at = updated_at
                    request_type.updated_by = "Noq"
                    write_obj = True

        for change_type in request_type.change_types:
            default_change_type = default_request_type_change_map[
                request_type.name
            ].get(change_type.name)
            init_template_types = sorted(change_type.template_types)
            init_supported_template_types = sorted(change_type.supported_template_types)
            if default_change_type:
                change_type.supported_template_types = sorted(default_change_type.supported_template_types)
            change_type.template_types = sorted(
                [tt for tt in change_type.supported_template_types if tt in tenant_template_types]
            )

            if not change_type.template_types and not change_type.deleted:
                # The tenant no longer supports this request type so remove it
                change_type.updated_by = "Noq"
                await change_type.delete()
                continue
            elif not init_template_types and bool(
                    change_type.template_types
            ):
                if change_type.updated_by == "Noq":
                    await change_type.reinitialize()
                    # The tenant now supports this request so un-delete it
                continue
            elif change_type.deleted:
                # No change was detected in request type usability so continue
                continue
            elif (
                    init_template_types != change_type.template_types
                    or init_supported_template_types != change_type.supported_template_types
            ):
                # The supported template types have changed so update the request type
                change_type.updated_at = updated_at
                change_type.updated_by = "Noq"
                await change_type.write()
                continue

            if change_type.created_by != "Noq" or change_type.updated_by not in [
                "Noq",
                None,
            ]:
                # User managed change type so skip
                continue
            elif not default_change_type:
                # This change type was managed and removed by Noq so remove it from the tenant
                await change_type.delete()
                write_obj = True
                continue

            for attr in [
                "description",
                "template_attribute",
                "apply_attr_behavior",
                "provider_definition_field",
            ]:
                if getattr(change_type, attr) != getattr(default_change_type, attr):
                    setattr(change_type, attr, getattr(default_change_type, attr))
                    change_type.updated_at = updated_at
                    change_type.updated_by = "Noq"
                    write_obj = True

            if (
                change_type.change_template.template
                != default_change_type.change_template.template
            ):
                change_type.updated_at = updated_at
                change_type.updated_by = "Noq"
                change_type.change_template.template = (
                    default_change_type.change_template.template
                )
                write_obj = True

            default_change_field_map = {
                cf.change_element: cf for cf in default_change_type.change_fields
            }
            # Update existing change fields
            for change_field in change_type.change_fields:
                default_change_field = default_change_field_map.get(
                    change_field.change_element
                )
                if not default_change_field:
                    await change_field.delete()
                    continue

                for field_attr in [
                    "field_key",
                    "field_type",
                    "field_text",
                    "description",
                    "allow_none",
                    "allow_multiple",
                    "max_char",
                    "validation_regex",
                    "options",
                    "typeahead_field_helper_id",
                    "default_value",
                ]:
                    if getattr(change_field, field_attr) != getattr(
                        default_change_field, field_attr
                    ):
                        setattr(
                            change_field,
                            field_attr,
                            getattr(default_change_field, field_attr),
                        )
                        write_obj = True

            # Add new change fields
            if len(default_change_type.change_fields) > len(change_type.change_fields):
                write_obj = True
                current_field_count = len(change_type.change_fields)
                for default_change_field in default_change_type.change_fields:
                    if default_change_field.change_element >= current_field_count:
                        default_change_field.change_type_id = change_type.id
                        change_type.change_fields.append(default_change_field)

        # Add new change types
        for default_change_type in default_request_type.change_types:
            if (
                default_change_type.name
                not in tenant_request_type_change_map[request_type.name]
            ):
                write_obj = True
                default_change_type.tenant_id = tenant.id
                default_change_type.request_type_id = request_type.id
                request_type.change_types.append(default_change_type)

        if write_obj:
            await request_type.write()

    # Add new request types
    new_request_types = []
    for default_request_type in default_request_types:
        if default_request_type.name not in tenant_request_type_map:
            default_request_type.tenant_id = tenant.id
            default_request_type.supported_template_types = [
                tt
                for tt in default_request_type.template_types
                if tt in tenant_template_types
            ]
            if default_request_type.supported_template_types:
                new_request_types.append(deepcopy(default_request_type))

    if new_request_types:
        await bulk_add(new_request_types)
