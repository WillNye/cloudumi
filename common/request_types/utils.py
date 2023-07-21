from operator import or_
from typing import Optional

from sqlalchemy import and_, cast, func, select
from sqlalchemy.orm import contains_eager, joinedload

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import TrustedProvider
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
    TypeAheadFieldHelper,
    user_favorited_change_type_association,
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
    request_type_id: Optional[str] = None,
    exclude_deleted: Optional[bool] = True,
    change_type_ids: Optional[list[str]] = None,
    summary_only: Optional[bool] = True,
    iambic_templates_specified: Optional[bool] = None,
) -> list[ChangeType]:
    async with ASYNC_PG_SESSION() as session:
        stmt = select(ChangeType).filter(ChangeType.tenant_id == tenant_id)

        if request_type_id:
            stmt = stmt.filter(ChangeType.request_type_id == request_type_id)
        if exclude_deleted:
            stmt = stmt.filter(ChangeType.deleted == False)
        if change_type_ids:
            stmt = stmt.filter(ChangeType.id.in_(change_type_ids))

        if iambic_templates_specified:
            stmt = stmt.filter(ChangeType.included_iambic_templates.any())

        if not summary_only:
            stmt = (
                stmt.join(RequestType, ChangeType.request_type_id == RequestType.id)
                .outerjoin(ChangeField, ChangeField.change_type_id == ChangeType.id)
                .outerjoin(
                    ChangeTypeTemplate,
                    ChangeTypeTemplate.change_type_id == ChangeType.id,
                )
                .outerjoin(
                    TypeAheadFieldHelper,
                    TypeAheadFieldHelper.id == ChangeField.typeahead_field_helper_id,
                )
                .outerjoin(ChangeType.included_iambic_template_provider_definition)
            )

            items = await session.execute(
                stmt.options(
                    contains_eager(ChangeType.request_type),
                    contains_eager(ChangeType.change_fields).options(
                        joinedload(ChangeField.typeahead)
                    ),
                    contains_eager(ChangeType.change_template),
                    joinedload(ChangeType.included_iambic_template_provider_definition),
                )
            )

            return items.scalars().unique().all()

        stmt = stmt.order_by(ChangeType.name)
        items = await session.execute(stmt)
        return items.scalars().all()


async def self_service_list_tenant_change_types(
    tenant_id: int,
    user_id: str,
    request_type_id: str,
    template_type: str = None,
    only_boosted: bool = False,
) -> list[ChangeType]:
    optional_filters = (
        [ChangeType.template_types.any(template_type)] if template_type else []
    )
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(ChangeType)
            .filter(
                ChangeType.tenant_id == tenant_id,
                ChangeType.request_type_id == request_type_id,
                ChangeType.deleted == False,
                *optional_filters
            )
            .outerjoin(
                user_favorited_change_type_association,
                and_(
                    user_favorited_change_type_association.c.change_type_id
                    == ChangeType.id,
                    user_favorited_change_type_association.c.user_id == user_id,
                ),
            )
            .add_columns(
                func.count(
                    user_favorited_change_type_association.c.change_type_id
                ).label("is_favorite")
            )
            .group_by(
                ChangeType,
                user_favorited_change_type_association.c.change_type_id,
            )
        )

        if only_boosted:
            stmt = stmt.having(
                or_(
                    func.count(user_favorited_change_type_association.c.change_type_id)
                    > 0,
                    ChangeType.suggest_to_all == True,
                )
            )

        stmt = stmt.order_by(
            func.count(user_favorited_change_type_association.c.change_type_id).desc(),
            ChangeType.suggest_to_all.desc(),
            ChangeType.name,
        )
        values = await session.execute(stmt)
        change_types = []
        for val in values:
            change_type = val[0]
            change_type.is_favorite = bool(val[1])
            change_types.append(change_type)

        return change_types


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
