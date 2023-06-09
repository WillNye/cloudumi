import functools
import json
import random
import uuid
from io import StringIO
from typing import Optional

from iambic.core.utils import transform_comments, yaml
from iambic.plugins.v0_1_0.aws.iam.policy.models import AWS_MANAGED_POLICY_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.role.models import (
    AWS_IAM_ROLE_TEMPLATE_TYPE,
    AwsIamRoleTemplate,
)
from sqlalchemy import func as sql_func
from sqlalchemy import select

from common import (
    IambicTemplate,
    IambicTemplateProviderDefinition,
    Request,
    RequestComment,
    Tenant,
    TenantProviderDefinition,
)
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.templates.utils import get_template_by_id
from common.iambic_request.request_crud import get_request, list_requests
from common.iambic_request.utils import generate_updated_iambic_template
from common.models import (
    SelfServiceRequestChangeType,
    SelfServiceRequestChangeTypeField,
    SelfServiceRequestData,
)
from common.request_types.utils import list_tenant_request_types
from qa import TENANT_SUMMARY
from qa.utils import generic_api_create_or_update_request, generic_api_get_request


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
        )
        if "AWS::IAM" in template_type:
            stmt = stmt.filter(
                IambicTemplate.file_path.like("%multi_account%"),
                ~IambicTemplate.resource_id.ilike("%aws%"),
                ~IambicTemplate.resource_id.ilike("%cognito%"),
            )

        stmt = stmt.group_by(
            IambicTemplateProviderDefinition.iambic_template_id
        ).having(
            sql_func.count(IambicTemplateProviderDefinition.iambic_template_id) > 2,
            sql_func.count(IambicTemplateProviderDefinition.iambic_template_id) < 10,
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


async def get_s3_permission_template_for_role_request_data() -> SelfServiceRequestData:
    tenant = TENANT_SUMMARY.tenant
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

    policy_number = random.randint(1, 1000)
    for tpd in tenant_provider_definitions[:-1]:
        account_name = tpd.definition["account_name"]
        self_service_request.changes.append(
            SelfServiceRequestChangeType(
                change_type_id=str(change_type.id),
                provider_definition_ids=[str(tpd.id)],
                fields=[
                    SelfServiceRequestChangeTypeField(
                        field_key="policy_name",
                        field_value=f"test-policy-{policy_number}",
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
    return self_service_request


async def generate_s3_permission_template_for_role():
    tenant = TENANT_SUMMARY.tenant
    self_service_request = await get_s3_permission_template_for_role_request_data(
        tenant
    )
    iambic_template = await generate_updated_iambic_template(
        tenant.id, self_service_request
    )
    return iambic_template


async def generate_s3_permission_template_for_managed_policy():
    tenant = TENANT_SUMMARY.tenant
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
    tenant = TENANT_SUMMARY.tenant
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


async def api_self_service_request_create():
    request_data = await get_s3_permission_template_for_role_request_data()

    validated_data = generic_api_create_or_update_request(
        "post",
        "v4/self-service/requests/validate",
        **request_data.dict(
            exclude_unset=False, exclude_defaults=False, exclude_none=True
        ),
    )
    return generic_api_create_or_update_request(
        "post",
        "v4/self-service/requests",
        **validated_data["data"],
    )


async def get_or_create_self_service_request() -> Request:
    # List Pending self-service requests
    # If none, call api_create_self_service_request and use that
    tenant = TENANT_SUMMARY.tenant
    requests = await list_requests(tenant.id, status__exact="Pending")
    if requests:
        return random.choice(requests)

    new_request = await api_self_service_request_create()
    request_id = new_request["data"]["request_id"]
    return await get_request(tenant.id, request_id)


def default_request_setter():
    def wrapper(func):
        @functools.wraps(func)
        async def inner(*args, **kwargs):
            if not kwargs.get("request") and not any(
                isinstance(arg, Request) for arg in args
            ):
                kwargs["request"] = await get_or_create_self_service_request()
            return await func(*args, **kwargs)

        return inner

    return wrapper


@default_request_setter()
async def api_self_service_request_get(request: Optional[Request]):
    return generic_api_get_request(f"v4/self-service/requests/{request.id}")


async def api_self_service_request_list(**params):
    return generic_api_get_request("v4/self-service/requests", **params)


@default_request_setter()
async def api_self_service_request_update(request: Optional[Request]):
    response_dict = await api_self_service_request_get(request)
    request_id = response_dict["data"]["request_id"]
    change_summary = response_dict["data"]["files"][0]
    file_path = change_summary["file_path"]
    iambic_template = yaml.load(StringIO(change_summary["template_body"]))
    template_description = iambic_template["properties"]["description"]
    if isinstance(template_description, str):
        iambic_template["properties"][
            "description"
        ] = f"{template_description} as part of {request_id}"
    else:
        template_description = template_description[0]["description"]
        iambic_template["properties"]["description"][0][
            "description"
        ] = f"{template_description} as part of {request_id}"

    iambic_template = AwsIamRoleTemplate(
        file_path=file_path, **transform_comments(iambic_template)
    )
    return generic_api_create_or_update_request(
        "put",
        f"v4/self-service/requests/{request_id}",
        file_path=file_path,
        template_body=iambic_template.get_body(),
        justification=response_dict["data"]["justification"],
    )


@default_request_setter()
async def api_self_service_request_approve(request: Optional[Request]):
    # return generic_api_create_or_update_request(
    #     "patch",
    #     f"v4/self-service/requests/{request.id}",
    #     status="approved",
    # )
    raise NotImplementedError


@default_request_setter()
async def api_self_service_request_deny(request: Optional[Request]):
    return generic_api_create_or_update_request(
        "patch",
        f"v4/self-service/requests/{request.id}",
        status="rejected",
    )


@default_request_setter()
async def api_self_service_request_comment_create(request: Optional[Request]):
    generic_api_create_or_update_request(
        "post",
        f"v4/self-service/requests/{request.id}/comments",
        body=f"This is my test comment - {random.randint(0, 1000)}",
    )
    return await api_self_service_request_get(request)


@default_request_setter()
async def api_self_service_request_comment_update(request: Optional[Request]):
    async with ASYNC_PG_SESSION() as session:
        results = await session.execute(
            select(RequestComment).where(RequestComment.request_id == request.id)
        )
        comments = results.scalars().all()
        comment = random.choice(comments)
    generic_api_create_or_update_request(
        "patch",
        f"v4/self-service/requests/{request.id}/comments/{comment.id}",
        body=f"This is my updated test comment - {random.randint(0, 1000)}",
    )
    return await api_self_service_request_get(request)
