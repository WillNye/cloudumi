from sqlalchemy import and_, cast, select
from sqlalchemy.orm import contains_eager, joinedload

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import TrustedProvider
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
    TypeAheadFieldHelper,
)


async def list_provider_typeahead_field_helpers(
    provider: str,
) -> list[TypeAheadFieldHelper]:
    async with ASYNC_PG_SESSION() as session:
        stmt = select(TypeAheadFieldHelper).filter(
            TypeAheadFieldHelper.provider == cast(provider, TrustedProvider)
        )
        items = await session.execute(stmt)

    return items.scalars().all()


async def list_tenant_request_types(
    tenant_id: int,
    provider: str = None,
    summary_only: bool = True,
    exclude_deleted: bool = True,
) -> list[RequestType]:
    async with ASYNC_PG_SESSION() as session:
        stmt = select(RequestType).filter(RequestType.tenant_id == tenant_id)
        if provider:
            stmt = stmt.filter(RequestType.provider == cast(provider, TrustedProvider))

        if exclude_deleted:
            stmt = stmt.filter(RequestType.deleted == False)

        if summary_only:
            items = await session.execute(stmt)
            return items.scalars().all()
        else:
            if exclude_deleted:
                stmt = stmt.outerjoin(
                    ChangeType,
                    and_(
                        ChangeType.request_type_id == RequestType.id,
                        ChangeType.tenant_id == RequestType.tenant_id,
                        ChangeType.deleted == False,
                    ),
                )
            else:
                stmt = stmt.outerjoin(
                    ChangeType,
                    and_(
                        ChangeType.request_type_id == RequestType.id,
                        ChangeType.tenant_id == RequestType.tenant_id,
                    ),
                )

            stmt = stmt.order_by(RequestType.name)
            items = await session.execute(
                stmt.options(
                    contains_eager(RequestType.change_types).options(
                        joinedload(ChangeType.change_fields),
                        joinedload(ChangeType.change_template),
                    )
                )
            )

            return items.scalars().unique().all()


async def list_tenant_change_types(
    tenant_id: int,
    request_type_id: str = None,
    exclude_deleted: bool = True,
) -> list[ChangeType]:
    async with ASYNC_PG_SESSION() as session:
        stmt = select(ChangeType).filter(ChangeType.tenant_id == tenant_id)

        if request_type_id:
            stmt = stmt.filter(ChangeType.request_type_id == request_type_id)
        if exclude_deleted:
            stmt = stmt.filter(ChangeType.deleted == False)

        stmt = stmt.order_by(ChangeType.name)
        items = await session.execute(stmt)
        return items.scalars().all()


async def get_tenant_change_type(tenant_id: int, change_type_id: str) -> ChangeType:
    async with ASYNC_PG_SESSION() as session:
        stmt = select(ChangeType).filter(
            and_(ChangeType.id == change_type_id, ChangeType.tenant_id == tenant_id)
        )
        stmt = (
            stmt.outerjoin(ChangeField, ChangeField.change_type_id == ChangeType.id)
            .outerjoin(
                ChangeTypeTemplate, ChangeTypeTemplate.change_type_id == ChangeType.id
            )
            .outerjoin(
                TypeAheadFieldHelper,
                TypeAheadFieldHelper.id == ChangeField.typeahead_field_helper_id,
            )
        )

        items = await session.execute(
            stmt.options(
                contains_eager(ChangeType.change_fields).options(
                    joinedload(ChangeField.typeahead)
                ),
                contains_eager(ChangeType.change_template),
            )
        )

        return items.scalars().unique().one_or_none()
