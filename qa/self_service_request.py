import asyncio
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
from iambic.plugins.v0_1_0.aws.identity_center.permission_set.models import (
    AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
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
from common.aws.iam.policy.utils import (
    get_aws_managed_policy_arns,
    list_customer_managed_policy_definitions,
)
from common.config.globals import ASYNC_PG_SESSION
from common.iambic.config.utils import list_tenant_provider_definitions
from common.iambic.templates.utils import get_template_by_id, list_tenant_templates
from common.iambic_request.request_crud import get_request, list_requests
from common.iambic_request.utils import generate_updated_iambic_template
from common.models import (
    SelfServiceRequestChangeType,
    SelfServiceRequestChangeTypeField,
    SelfServiceRequestData,
)
from common.request_types.models import ChangeType
from common.request_types.utils import (
    list_tenant_change_types,
    list_tenant_request_types,
)
from qa import TENANT_SUMMARY
from qa.request_types import api_self_service_change_types_list
from qa.utils import generic_api_create_or_update_request, generic_api_get_request


async def get_change_type_by_name(
    name: str,
    related_template: Optional[str] = None,
) -> ChangeType:
    change_types = await list_tenant_change_types(
        TENANT_SUMMARY.tenant.id, summary_only=False
    )
    if related_template:
        return next(
            ct
            for ct in change_types
            if ct.name == name and related_template in ct.template_types
        )
    return next(ct for ct in change_types if ct.name == name)


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
    change_type = await get_change_type_by_name("S3", AWS_IAM_ROLE_TEMPLATE_TYPE)
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
                        field_value=f"qa-run-policy-{policy_number}",
                    ),
                    SelfServiceRequestChangeTypeField(
                        field_key="s3_buckets",
                        field_value=[
                            f"arn:aws:s3:::{account_name}-bucket-{elem}"
                            for elem in range(1, 4)
                        ],
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
    self_service_request = await get_s3_permission_template_for_role_request_data()
    iambic_template = await generate_updated_iambic_template(
        tenant, self_service_request
    )
    print(
        json.dumps(
            iambic_template.dict(exclude_unset=False, exclude_defaults=True), indent=2
        )
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
    change_type = await get_change_type_by_name("S3", AWS_MANAGED_POLICY_TEMPLATE_TYPE)
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
                        field_key="s3_buckets",
                        field_value=[
                            f"arn:aws:s3:::{account_name}-bucket-{elem}"
                            for elem in range(1, 4)
                        ],
                    ),
                    SelfServiceRequestChangeTypeField(
                        field_key="s3_permissions",
                        field_value=["Get and List", "Create and Update (Put)"],
                    ),
                ],
            )
        )

    iambic_template = await generate_updated_iambic_template(
        tenant, self_service_request
    )
    print(
        json.dumps(
            iambic_template.dict(exclude_unset=False, exclude_defaults=True), indent=2
        )
    )
    return iambic_template


async def generate_permission_set_customer_policy_attachment_template():
    # Get the proper change type
    change_type = await get_change_type_by_name(
        "Attach a customer managed policy to a permission set"
    )

    # Get the relevant AWS Account
    aws_orgs = await list_tenant_provider_definitions(
        TENANT_SUMMARY.tenant.id, provider="aws", sub_type="organizations"
    )
    aws_org = aws_orgs[0]
    account_id = aws_org.definition["org_account_id"]
    aws_account = await list_tenant_provider_definitions(
        TENANT_SUMMARY.tenant.id, provider="aws", name=account_id
    )
    aws_account = aws_account[0]

    # Get the target AWS PermissionSet
    permission_sets = await list_tenant_templates(
        TENANT_SUMMARY.tenant.id,
        template_type=AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
    )
    permission_set = random.choice(permission_sets)

    # Get the referenced AWS Customer Managed Policy
    aws_customer_managed_policies = await list_tenant_templates(
        TENANT_SUMMARY.tenant.id,
        template_type=AWS_MANAGED_POLICY_TEMPLATE_TYPE,
        provider_definition_ids=[aws_account.id],
    )
    customer_managed_policy = random.choice(aws_customer_managed_policies)

    self_service_request = SelfServiceRequestData(
        id=uuid.uuid4(),
        iambic_template_id=str(permission_set.id),
        justification="Testing",
        expires_at="In 1 days",
        changes=[],
    )

    self_service_request.changes.append(
        SelfServiceRequestChangeType(
            change_type_id=str(change_type.id),
            provider_definition_ids=[],
            fields=[
                SelfServiceRequestChangeTypeField(
                    field_key="policy",
                    field_value=str(customer_managed_policy.id),
                ),
            ],
        )
    )

    iambic_template = await generate_updated_iambic_template(
        TENANT_SUMMARY.tenant, self_service_request
    )
    print(
        json.dumps(
            iambic_template.dict(exclude_unset=False, exclude_defaults=True), indent=2
        )
    )
    return iambic_template


async def generate_permission_set_aws_managed_policy_attachment_template():
    change_type = await get_change_type_by_name(
        "Attach an AWS managed policy to a permission set"
    )

    # Get the target AWS PermissionSet
    permission_sets = await list_tenant_templates(
        TENANT_SUMMARY.tenant.id,
        template_type=AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
    )
    permission_set = random.choice(permission_sets)

    # Get the referenced AWS Managed Policy
    aws_managed_policies = await get_aws_managed_policy_arns()
    aws_managed_policy = random.choice(aws_managed_policies)

    self_service_request = SelfServiceRequestData(
        id=uuid.uuid4(),
        iambic_template_id=str(permission_set.id),
        justification="Testing",
        expires_at="In 1 days",
        changes=[],
    )

    self_service_request.changes.append(
        SelfServiceRequestChangeType(
            change_type_id=str(change_type.id),
            provider_definition_ids=[],
            fields=[
                SelfServiceRequestChangeTypeField(
                    field_key="policy_arn",
                    field_value=str(aws_managed_policy),
                ),
            ],
        )
    )

    iambic_template = await generate_updated_iambic_template(
        TENANT_SUMMARY.tenant, self_service_request
    )
    print(
        json.dumps(
            iambic_template.dict(exclude_unset=False, exclude_defaults=True), indent=2
        )
    )
    return iambic_template


async def generate_role_policy_attachment_template():
    change_type = await get_change_type_by_name("Attach a managed policy")

    # Get the relevant AWS Account
    aws_orgs = await list_tenant_provider_definitions(
        TENANT_SUMMARY.tenant.id, provider="aws", sub_type="organizations"
    )
    aws_org = aws_orgs[0]
    account_id = aws_org.definition["org_account_id"]
    aws_account = await list_tenant_provider_definitions(
        TENANT_SUMMARY.tenant.id, provider="aws", name=account_id
    )
    aws_account = aws_account[0]

    # Get the target AWS PermissionSet
    iam_roles = await list_tenant_templates(
        TENANT_SUMMARY.tenant.id,
        template_type=AWS_IAM_ROLE_TEMPLATE_TYPE,
        provider_definition_ids=[str(aws_account.id)],
    )
    iam_role = random.choice(iam_roles)

    # Get the referenced AWS Customer Managed Policy
    manged_policies = await list_customer_managed_policy_definitions(
        TENANT_SUMMARY.tenant,
        provider_definition_ids=[str(aws_account.id)],
    )
    managed_policy = random.choice(manged_policies)

    self_service_request = SelfServiceRequestData(
        id=uuid.uuid4(),
        iambic_template_id=str(iam_role.id),
        justification="Testing",
        expires_at="In 1 days",
        changes=[],
    )

    self_service_request.changes.append(
        SelfServiceRequestChangeType(
            change_type_id=str(change_type.id),
            provider_definition_ids=[str(aws_account.id)],
            fields=[
                SelfServiceRequestChangeTypeField(
                    field_key="policy_arn",
                    field_value=str(managed_policy.secondary_resource_id),
                ),
            ],
        )
    )

    iambic_template = await generate_updated_iambic_template(
        TENANT_SUMMARY.tenant, self_service_request
    )
    print(
        json.dumps(
            iambic_template.dict(exclude_unset=False, exclude_defaults=True), indent=2
        )
    )
    return iambic_template


async def generate_request_role_access_request_data(user_request: bool = True):
    tenant = TENANT_SUMMARY.tenant
    (
        template,
        tenant_provider_definitions,
    ) = await get_template_and_provider_definition_by_template_type(
        tenant, AWS_IAM_ROLE_TEMPLATE_TYPE
    )
    change_type_name = (
        "Noq User access request" if user_request else "Noq Group access request"
    )
    change_type = await get_change_type_by_name(
        change_type_name, AWS_IAM_ROLE_TEMPLATE_TYPE
    )
    self_service_request = SelfServiceRequestData(
        id=uuid.uuid4(),
        iambic_template_id=str(template.id),
        justification="Testing",
        expires_at="In 1 days",
        changes=[],
    )
    if user_request:
        field = SelfServiceRequestChangeTypeField(
            field_key="noq_email", field_value="user@noq.dev"
        )
    else:
        field = SelfServiceRequestChangeTypeField(
            field_key="noq_group", field_value="engineering@noq.dev"
        )

    for tpd in tenant_provider_definitions[:-1]:
        self_service_request.changes.append(
            SelfServiceRequestChangeType(
                change_type_id=str(change_type.id),
                provider_definition_ids=[str(tpd.id)],
                fields=[field],
            )
        )

    return self_service_request


async def generate_request_role_access_request_role_template():
    tenant = TENANT_SUMMARY.tenant
    self_service_request = await generate_request_role_access_request_data()
    iambic_template = await generate_updated_iambic_template(
        tenant, self_service_request
    )
    print(
        json.dumps(
            iambic_template.dict(exclude_unset=False, exclude_defaults=True), indent=2
        )
    )
    return iambic_template


async def api_service_service_request_validate(
    request_data: SelfServiceRequestData = None,
):
    if not request_data:
        request_data = await get_s3_permission_template_for_role_request_data()

    return generic_api_create_or_update_request(
        "post",
        "v4/self-service/requests/validate",
        **request_data.dict(
            exclude_unset=False, exclude_defaults=False, exclude_none=True
        ),
    )


async def api_self_service_request_create(
    request_data: SelfServiceRequestData = None,
) -> dict:
    validated_data = await api_service_service_request_validate(request_data)
    response_data = generic_api_create_or_update_request(
        "post",
        "v4/self-service/requests",
        **validated_data["data"]["request_data"],
    )
    print("Waiting 30 seconds for the noq-saas-iambic-integrations bot to run")
    await asyncio.sleep(30)
    return response_data


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
    template_description = iambic_template["properties"].get(
        "description", "Role description"
    )
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
    """
    Requires:
    lt --port 8092 --subdomain {your_github_app}
    API Running
    Celery Running
    """
    return generic_api_create_or_update_request(
        "patch",
        f"v4/self-service/requests/{request.id}",
        status="approved",
    )


@default_request_setter()
async def api_self_service_request_apply(request: Optional[Request]):
    """
    Requires:
    lt --port 8092 --subdomain {your_github_app}
    API Running
    Celery Running
    """
    return generic_api_create_or_update_request(
        "patch",
        f"v4/self-service/requests/{request.id}",
        status="apply",
    )


@default_request_setter()
async def api_self_service_request_deny(request: Optional[Request]):
    """
    Requires:
    lt --port 8092 --subdomain {your_github_app}
    API Running
    Celery Running
    """
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


async def api_end_to_end_access_request(user_request: bool):
    """Creates, approves, and applies an IAMbic request.

    if user_request is true it will generate a user request, otherwise it will generate a group request

    Requires:
    lt --port 8092 --subdomain {your_github_app}
    API Running
    Celery Running
    """
    request_response = await api_self_service_request_create(
        await generate_request_role_access_request_data(user_request=user_request)
    )
    request_id = request_response["data"]["request_id"]
    return await api_self_service_request_approve(
        await get_request(TENANT_SUMMARY.tenant.id, request_id)
    )


async def get_or_create_self_service_request_curated():
    tenant = TENANT_SUMMARY.tenant
    # 1. User selects AWS Provider
    # 2. FE Calls BE to get list of request types
    request_types = await list_tenant_request_types(
        tenant.id, "aws", summary_only=False
    )
    # 3. User selects "Add Permissions to Identity"
    request_type = [
        r for r in request_types if r.name == "Add permissions to identity"
    ][0]
    # 4. FE Calls BE to get list of "curated" change types that already have an identity (a.k.a iambic template) specified
    change_types = await api_self_service_change_types_list(
        str(request_type.id), iambic_templates_specified=True
    )
    # 5. User selects curated request type, which already has an iambic template specified,
    print(change_types)


async def run_all_template_generators():
    _ = await generate_s3_permission_template_for_role()
    _ = await generate_s3_permission_template_for_managed_policy()
    _ = await generate_permission_set_customer_policy_attachment_template()
    _ = await generate_permission_set_aws_managed_policy_attachment_template()
    _ = await generate_role_policy_attachment_template()
    _ = await generate_request_role_access_request_role_template()


if __name__ == "__main__":
    asyncio.run(TENANT_SUMMARY.setup())
    asyncio.run(get_or_create_self_service_request_curated())
