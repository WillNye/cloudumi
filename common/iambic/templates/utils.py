from typing import Optional, Union

from iambic.core.utils import sanitize_string
from iambic.plugins.v0_1_0.aws.models import AWSAccount
from jinja2 import BaseLoader
from jinja2.sandbox import ImmutableSandboxedEnvironment
from sqlalchemy import or_, select
from sqlalchemy.orm import contains_eager

from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.models import TenantProviderDefinition
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
    template_ids: Optional[list[str]] = None,
    template_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    provider_definition_ids: Optional[list[str]] = None,
    exclude_template_provider_def: Optional[bool] = True,
    exclude_template_content: Optional[bool] = True,
    page_size: Optional[int] = None,
    page: Optional[int] = 1,
) -> list[IambicTemplate]:
    if resource_id:
        assert (
            template_type
        ), "template_type query param must be provided if resource_id is provided"

    async with ASYNC_PG_SESSION() as session:
        options = []

        stmt = select(IambicTemplate).filter(IambicTemplate.tenant_id == tenant_id)
        if template_ids:
            stmt = stmt.filter(IambicTemplate.id.in_(template_ids))
        if template_type:
            stmt = stmt.filter(IambicTemplate.template_type == template_type)

        if resource_id or provider_definition_ids or not exclude_template_provider_def:
            stmt = stmt.join(
                IambicTemplateProviderDefinition,
                IambicTemplateProviderDefinition.iambic_template_id
                == IambicTemplate.id,
            )

        if resource_id:
            stmt = stmt.filter(
                or_(
                    IambicTemplate.resource_id.ilike(f"%{resource_id}%"),
                    IambicTemplateProviderDefinition.resource_id.ilike(
                        f"%{resource_id}%"
                    ),
                )
            )

        if not exclude_template_provider_def:
            options.append(contains_eager(IambicTemplate.provider_definition_refs))

        if provider_definition_ids:
            stmt = stmt.filter(
                IambicTemplateProviderDefinition.tenant_provider_definition_id.in_(
                    provider_definition_ids
                )
            )

        if not exclude_template_content:
            stmt = stmt.join(
                IambicTemplateContent,
                IambicTemplateContent.iambic_template_id == IambicTemplate.id,
            )
            options.append(contains_eager(IambicTemplate.content))

        if options:
            stmt = stmt.options(*options)

        if template_type:
            stmt = stmt.order_by(IambicTemplate.resource_id)
        else:
            stmt = stmt.order_by(
                IambicTemplate.resource_type, IambicTemplate.resource_id
            )

        if page_size:
            stmt = stmt.slice((page - 1) * page_size, page * page_size)

        items = await session.execute(stmt)
        return items.scalars().unique().all()


def get_template_str_value_for_provider_definition(
    template_str_attr, provider_definition: Union[TenantProviderDefinition, AWSAccount]
) -> str:
    valid_characters_re = r"[\w_+=,.@-]"
    variables = {var.key: var.value for var in provider_definition.variables}
    if not isinstance(provider_definition, TenantProviderDefinition):
        for extra_attr in {"account_id", "account_name", "owner"}:
            if attr_val := getattr(provider_definition, extra_attr, None):
                variables[extra_attr] = attr_val

    variables = {
        k: sanitize_string(v, valid_characters_re) for k, v in variables.items()
    }
    rtemplate = ImmutableSandboxedEnvironment(loader=BaseLoader()).from_string(
        template_str_attr
    )
    return rtemplate.render(var=variables)
