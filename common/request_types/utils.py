from sqlalchemy import and_, cast, select
from sqlalchemy.orm import contains_eager, joinedload

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import TrustedProvider
from common.request_types.models import ChangeType, RequestType, TypeAheadFieldHelper


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
):
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
                        ChangeType.deleted == False,
                    ),
                )
            else:
                stmt = stmt.outerjoin(
                    ChangeType, ChangeType.request_type_id == RequestType.id
                )

            items = await session.execute(
                stmt.options(
                    contains_eager(RequestType.change_types).options(
                        joinedload(ChangeType.change_fields),
                        joinedload(ChangeType.change_template),
                    )
                )
            )

            return items.scalars().unique().all()
