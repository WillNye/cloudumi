from operator import or_
from typing import Optional

from sqlalchemy import and_, cast, func, select
from sqlalchemy.orm import contains_eager, joinedload, selectinload

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import TrustedProvider
from common.iambic.templates.models import IambicTemplateProviderDefinition
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    ExpressAccessRequest,
    RequestType,
    TypeAheadFieldHelper,
    user_favorited_change_type_association,
    user_favorited_express_access_request_association,
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
    boosted_only: bool = False,
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

        if boosted_only:
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
            # This is a way to future-proof the inclusion of suggestion rules
            # e.g. suggest this change type if the user is in a certain group
            change_type.is_suggested = change_type.suggest_to_all
            change_type.is_favorite = bool(val[1])
            change_types.append(change_type)

        return change_types


async def self_service_list_tenant_express_access_requests(
    tenant_id: int,
    user_id: str,
    provider: str = None,
    boosted_only: bool = False,
) -> list[ExpressAccessRequest]:
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(ExpressAccessRequest)
            .filter(
                ExpressAccessRequest.tenant_id == tenant_id,
                ExpressAccessRequest.deleted == False,
            )
            .outerjoin(
                user_favorited_express_access_request_association,
                and_(
                    user_favorited_express_access_request_association.c.express_access_request_id
                    == ExpressAccessRequest.id,
                    user_favorited_express_access_request_association.c.user_id
                    == user_id,
                ),
            )
            .add_columns(
                func.count(
                    user_favorited_express_access_request_association.c.express_access_request_id
                ).label("is_favorite")
            )
            .group_by(
                ExpressAccessRequest,
                user_favorited_express_access_request_association.c.express_access_request_id,
            )
        )

        if provider:
            stmt = (
                stmt.join(
                    ChangeType, ChangeType.id == ExpressAccessRequest.change_type_id
                )
                .join(RequestType, RequestType.id == ChangeType.request_type_id)
                .filter(RequestType.provider == provider)
            )

        if boosted_only:
            stmt = stmt.having(
                or_(
                    func.count(
                        user_favorited_express_access_request_association.c.express_access_request_id
                    )
                    > 0,
                    ExpressAccessRequest.suggest_to_all == True,
                )
            )

        stmt = stmt.order_by(
            func.count(
                user_favorited_express_access_request_association.c.express_access_request_id
            ).desc(),
            ExpressAccessRequest.suggest_to_all.desc(),
            ExpressAccessRequest.name,
        )
        values = await session.execute(stmt)
        express_access_requests = []
        for val in values:
            express_access_request = val[0]
            # This is a way to future-proof the inclusion of suggestion rules
            # e.g. suggest this change type if the user is in a certain group
            express_access_request.is_suggested = express_access_request.suggest_to_all
            express_access_request.is_favorite = bool(val[1])
            express_access_requests.append(express_access_request)

        return express_access_requests


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


async def self_service_get_tenant_express_access_request(
    tenant_id: int, user_id: str, express_access_request_id: str
) -> ExpressAccessRequest:
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(ExpressAccessRequest)
            .filter(
                ExpressAccessRequest.id == express_access_request_id,
                ExpressAccessRequest.tenant_id == tenant_id,
                ExpressAccessRequest.deleted == False,
            )
            .join(
                ChangeType,
                and_(
                    ExpressAccessRequest.change_type_id == ChangeType.id,
                    ChangeType.tenant_id == tenant_id,
                ),
            )
            .options(
                selectinload(
                    ExpressAccessRequest.iambic_template_provider_defs
                ).options(
                    joinedload(
                        IambicTemplateProviderDefinition.tenant_provider_definition
                    )
                ),
                contains_eager(ExpressAccessRequest.change_type).options(
                    joinedload(ChangeType.favorited_by),
                    joinedload(ChangeType.change_fields).joinedload(
                        ChangeField.typeahead
                    ),
                    joinedload(ChangeType.change_template),
                ),
            )
        )
        values = await session.execute(stmt)
        express_access_request = values.scalars().unique().one_or_none()
        if express_access_request:
            # This is a way to future-proof the inclusion of suggestion rules
            # e.g. suggest this change type if the user is in a certain group
            express_access_request.change_type.is_suggested = (
                express_access_request.suggest_to_all
            )
            express_access_request.change_type.is_favorite = bool(
                [
                    fav
                    for fav in express_access_request.change_type.favorited_by
                    if fav.user_id == user_id
                ]
            )

        return express_access_request


async def get_tenant_express_access_request(
    tenant_id: int, express_access_request_id: str
) -> ExpressAccessRequest:
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(ExpressAccessRequest)
            .filter(
                ExpressAccessRequest.id == express_access_request_id,
                ExpressAccessRequest.tenant_id == tenant_id,
                ExpressAccessRequest.deleted == False,
            )
            .options(
                selectinload(
                    ExpressAccessRequest.iambic_template_provider_defs
                ).options(
                    joinedload(
                        IambicTemplateProviderDefinition.tenant_provider_definition
                    )
                ),
            )
        )
        values = await session.execute(stmt)
        return values.scalars().unique().one_or_none()
