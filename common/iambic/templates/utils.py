from iambic.core.utils import sanitize_string
from iambic.plugins.v0_1_0.aws.models import AWSAccount
from jinja2 import BaseLoader, Environment
from sqlalchemy import or_, select
from sqlalchemy.orm import contains_eager

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.templates.models import (
    IambicTemplate,
    IambicTemplateContent,
    IambicTemplateProviderDefinition,
)


async def get_template_by_id(tenant_id: int, template_id: str) -> IambicTemplate:
    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(IambicTemplate)
            .filter(
                IambicTemplate.id == template_id,
                IambicTemplate.tenant_id == tenant_id,
            )
            .join(
                IambicTemplateContent,
                IambicTemplateContent.iambic_template_id == IambicTemplate.id,
            )
            .options(contains_eager(IambicTemplate.content))
        )

        items = await session.execute(stmt)
        return items.scalars().one()


async def list_tenant_templates(
    tenant_id: int,
    template_type: str = None,
    resource_id: str = None,
    page_size: int = None,
    page: int = 1,
) -> list[IambicTemplate]:
    if resource_id:
        assert (
            template_type
        ), "template_type query param must be provided if resource_id is provided"

    async with ASYNC_PG_SESSION() as session:
        stmt = select(IambicTemplate).filter(IambicTemplate.tenant_id == tenant_id)
        if template_type:
            stmt = stmt.filter(
                IambicTemplate.template_type == template_type
            )  # noqa: E712
        if resource_id:
            stmt = stmt.join(
                IambicTemplateProviderDefinition,
                IambicTemplateProviderDefinition.iambic_template_id
                == IambicTemplate.id,
            ).filter(
                or_(
                    IambicTemplate.resource_id.ilike(f"%{resource_id}%"),
                    IambicTemplateProviderDefinition.resource_id.ilike(
                        f"%{resource_id}%"
                    ),
                )
            )  # noqa: E712

        if template_type:
            stmt = stmt.order_by(IambicTemplate.resource_id)
        else:
            stmt = stmt.order_by(
                IambicTemplate.resource_type, IambicTemplate.resource_id
            )

        if page_size:
            stmt = stmt.slice((page - 1) * page_size, page * page_size)

        items = await session.execute(stmt)

    if resource_id:
        return items.scalars().unique().all()
    return items.scalars().all()


def get_template_str_value_for_aws_account(
    template_str_attr, aws_account: AWSAccount
) -> str:
    variables = {var.key: var.value for var in aws_account.variables}
    variables["account_id"] = aws_account.account_id
    variables["account_name"] = aws_account.account_name
    valid_characters_re = r"[\w_+=,.@-]"
    variables = {
        k: sanitize_string(v, valid_characters_re) for k, v in variables.items()
    }
    rtemplate = Environment(loader=BaseLoader()).from_string(template_str_attr)
    return rtemplate.render(var=variables)
