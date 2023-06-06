import json
import random
import uuid

from iambic.plugins.v0_1_0.aws.iam.policy.models import AWS_MANAGED_POLICY_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.role.models import AWS_IAM_ROLE_TEMPLATE_TYPE
from sqlalchemy import func as sql_func
from sqlalchemy import select

from common import (
    IambicTemplate,
    IambicTemplateProviderDefinition,
    Tenant,
    TenantProviderDefinition,
)
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.templates.utils import get_template_by_id
from common.iambic_request.utils import generate_updated_iambic_template
from common.models import (
    SelfServiceRequestChangeType,
    SelfServiceRequestChangeTypeField,
    SelfServiceRequestData,
)
from common.request_types.utils import list_tenant_request_types
from qa import TENANT_NAME


async def get_template_and_provider_definition_by_template_type(
    tenant: Tenant, template_type: str
):

    async with ASYNC_PG_SESSION() as session:
        stmt = (
            select(
                IambicTemplateProviderDefinition.iambic_template_id,
                sql_func.count(IambicTemplateProviderDefinition.iambic_template_id),
            )
            .join(
                IambicTemplate,
                IambicTemplateProviderDefinition.iambic_template_id
                == IambicTemplate.id,
            )
            .filter(
                IambicTemplateProviderDefinition.tenant_id == tenant.id,
                IambicTemplate.template_type == template_type,
            )
            .group_by(IambicTemplateProviderDefinition.iambic_template_id)
            .having(
                sql_func.count(IambicTemplateProviderDefinition.iambic_template_id) > 2,
                sql_func.count(IambicTemplateProviderDefinition.iambic_template_id)
                < 10,
            )
        )
        potential_templates = (await session.execute(stmt)).scalars().all()
        template_id = random.choice(potential_templates)
        template = await get_template_by_id(tenant.id, template_id)

        stmt = (
            select(TenantProviderDefinition)
            .join(
                IambicTemplateProviderDefinition,
                IambicTemplateProviderDefinition.tenant_provider_definition_id
                == TenantProviderDefinition.id,
            )
            .filter(IambicTemplateProviderDefinition.iambic_template_id == template.id)
        )
        tenant_provider_definitions = (await session.execute(stmt)).scalars().all()

        return template, tenant_provider_definitions


async def generate_s3_permission_template_for_role():
    tenant = await Tenant.get_by_name(TENANT_NAME)

    (
        template,
        tenant_provider_definitions,
    ) = await get_template_and_provider_definition_by_template_type(
        tenant, AWS_IAM_ROLE_TEMPLATE_TYPE
    )
    request_types = await list_tenant_request_types(
        tenant.id, "aws", summary_only=False
    )
    request_type = [
        r for r in request_types if r.name == "Add permissions to identity"
    ][0]
    change_type = [ct for ct in request_type.change_types if ct.name == "S3"][0]
    self_service_request = SelfServiceRequestData(
        id=uuid.uuid4(),
        iambic_template_id=str(template.id),
        justification="Testing",
        expires_at="In 1 days",
        changes=[],
    )

    for tpd in tenant_provider_definitions[:-1]:
        account_name = tpd.definition["account_name"]
        self_service_request.changes.append(
            SelfServiceRequestChangeType(
                change_type_id=str(change_type.id),
                provider_definition_ids=[str(tpd.id)],
                fields=[
                    SelfServiceRequestChangeTypeField(
                        field_key="policy_name", field_value="test-policy"
                    ),
                    SelfServiceRequestChangeTypeField(
                        field_key="s3_bucket",
                        field_value=f"arn:aws:s3:::{account_name}-bucket",
                    ),
                    SelfServiceRequestChangeTypeField(
                        field_key="s3_permissions",
                        field_value=["Get and List", "Create and Update (Put)"],
                    ),
                ],
            )
        )

    iambic_template = await generate_updated_iambic_template(
        tenant.id, self_service_request
    )
    print(
        json.dumps(
            iambic_template.dict(exclude_unset=False, exclude_defaults=True), indent=2
        )
    )
    return iambic_template


async def generate_s3_permission_template_for_managed_policy():
    tenant = await Tenant.get_by_name(TENANT_NAME)

    (
        template,
        tenant_provider_definitions,
    ) = await get_template_and_provider_definition_by_template_type(
        tenant, AWS_MANAGED_POLICY_TEMPLATE_TYPE
    )
    request_types = await list_tenant_request_types(
        tenant.id, "aws", summary_only=False
    )
    request_type = [
        r for r in request_types if r.name == "Add permissions to managed policy"
    ][0]
    change_type = [ct for ct in request_type.change_types if ct.name == "S3"][0]
    self_service_request = SelfServiceRequestData(
        id=uuid.uuid4(),
        iambic_template_id=str(template.id),
        justification="Testing",
        expires_at="In 1 days",
        changes=[],
    )

    for tpd in tenant_provider_definitions[:-1]:
        account_name = tpd.definition["account_name"]
        self_service_request.changes.append(
            SelfServiceRequestChangeType(
                change_type_id=str(change_type.id),
                provider_definition_ids=[str(tpd.id)],
                fields=[
                    SelfServiceRequestChangeTypeField(
                        field_key="s3_bucket",
                        field_value=f"arn:aws:s3:::{account_name}-bucket",
                    ),
                    SelfServiceRequestChangeTypeField(
                        field_key="s3_permissions",
                        field_value=["Get and List", "Create and Update (Put)"],
                    ),
                ],
            )
        )

    iambic_template = await generate_updated_iambic_template(
        tenant.id, self_service_request
    )
    print(
        json.dumps(
            iambic_template.dict(exclude_unset=False, exclude_defaults=True), indent=2
        )
    )
    return iambic_template


async def generate_request_role_access_template():
    tenant = await Tenant.get_by_name(TENANT_NAME)

    (
        template,
        tenant_provider_definitions,
    ) = await get_template_and_provider_definition_by_template_type(
        tenant, AWS_IAM_ROLE_TEMPLATE_TYPE
    )
    request_types = await list_tenant_request_types(
        tenant.id, "aws", summary_only=False
    )
    request_type = [
        r for r in request_types if r.name == "Request access to AWS IAM Role"
    ][0]
    change_type = [
        ct for ct in request_type.change_types if ct.name == "Noq User access request"
    ][0]
    self_service_request = SelfServiceRequestData(
        id=uuid.uuid4(),
        iambic_template_id=str(template.id),
        justification="Testing",
        expires_at="In 1 days",
        changes=[],
    )

    for tpd in tenant_provider_definitions[:-1]:
        self_service_request.changes.append(
            SelfServiceRequestChangeType(
                change_type_id=str(change_type.id),
                provider_definition_ids=[str(tpd.id)],
                fields=[
                    SelfServiceRequestChangeTypeField(
                        field_key="noq_email", field_value="user@noq.dev"
                    )
                ],
            )
        )

    iambic_template = await generate_updated_iambic_template(
        tenant.id, self_service_request
    )
    print(
        json.dumps(
            iambic_template.dict(exclude_unset=False, exclude_defaults=True), indent=2
        )
    )
    return iambic_template
