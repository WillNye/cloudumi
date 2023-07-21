from collections import defaultdict
from copy import deepcopy

from iambic.plugins.v0_1_0.aws.iam.group.models import AWS_IAM_GROUP_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.policy.models import AWS_MANAGED_POLICY_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.role.models import AWS_IAM_ROLE_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.user.models import AWS_IAM_USER_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.identity_center.permission_set.models import (
    AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
)
from policy_sentry.shared.iam_data import iam_definition

from common.iambic.config.models import TRUSTED_PROVIDER_RESOLVER_MAP
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
    TypeAheadFieldHelper,
)
from common.request_types.utils import list_provider_typeahead_field_helpers

aws_provider_resolver = TRUSTED_PROVIDER_RESOLVER_MAP["aws"]


def get_services_permissions() -> dict[dict[list[str]]]:
    """Returns a list of service permissions broken down by access level.

    Example:
        Alexa for Business (a4b)
            Write:
                a4b:ApproveSkill
                ...
    """

    service_permissions = defaultdict(lambda: defaultdict(set))

    for _, service_data in iam_definition.items():
        prefix = service_data["prefix"]
        service_name = f'{service_data["service_name"]} ({prefix})'

        for priv_name, priv_data in service_data["privileges"].items():
            service_permissions[service_name][priv_data["access_level"]].add(
                f"{prefix}:{priv_name}"
            )

    for service_name, access_level_data in service_permissions.items():
        for access_level, permissions in access_level_data.items():
            service_permissions[service_name][access_level] = sorted(list(permissions))

    return service_permissions


def _get_default_aws_request_permission_request_types(
    field_helper_map: dict[str:TypeAheadFieldHelper],
) -> RequestType:
    # Formatted like this to catch all RDS variants
    permission_changes = [
        ChangeType(
            name="RDS",
            description="Request permissions to an RDS resource.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="resource_arns",
                    field_type="TextBox",
                    field_text="RDS Resource ARN",
                    description="The RDS Resource ARN the selected identity requires permissions to. "
                    "You must provide the full ARN. Wildcards supported.",
                    allow_none=False,
                    allow_multiple=True,
                ),
                ChangeField(
                    change_element=1,
                    field_key="resource_permissions",
                    field_type="Choice",
                    field_text="Permission Options",
                    description="The RDS permissions to add",
                    allow_none=False,
                    allow_multiple=True,
                    options=[
                        {
                            "option_text": "RDS Data API",
                            "option_value": [
                                "rds-data:BatchExecuteStatement",
                                "rds-data:BeginTransaction",
                                "rds-data:CommitTransaction",
                                "rds-data:ExecuteStatement",
                                "rds-data:RollbackTransaction",
                            ],
                        },
                    ],
                ),
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
          "Action": ["{{form.resource_permissions|join('","')}}"],
          "Effect":"Allow",
          "Resource": ["{{form.resource_arns|join('","')}}"]
        }"""
            ),
            supported_template_types=[
                AWS_IAM_GROUP_TEMPLATE_TYPE,
                AWS_IAM_ROLE_TEMPLATE_TYPE,
                AWS_IAM_USER_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        ),
        ChangeType(
            name="S3",
            description="Add S3 permissions",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="s3_buckets",
                    field_type="TypeAhead",
                    field_text="S3 Bucket",
                    description="The S3 bucket the resource requires permissions to. "
                    "You must provide the full ARN. Wildcards supported.",
                    allow_none=False,
                    allow_multiple=True,
                    typeahead_field_helper_id=field_helper_map["S3 Bucket ARN"].id,
                ),
                ChangeField(
                    change_element=1,
                    field_key="s3_permissions",
                    field_type="Choice",
                    field_text="Permission Options",
                    description="The S3 permissions to add",
                    allow_none=False,
                    allow_multiple=True,
                    options=[
                        {
                            "option_text": "Get and List",
                            "option_value": [
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                                "s3:GetBucket*",
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                            ],
                        },
                        {
                            "option_text": "Create and Update (Put)",
                            "option_value": [
                                "s3:PutObject",
                                "s3:PutObjectTagging",
                                "s3:PutObjectVersionTagging",
                                "s3:PutObjectLegalHold",
                                "s3:ListMultipartUploadParts*",
                                "s3:PutObjectRetention*",
                                "s3:Abort*",
                            ],
                        },
                        {
                            "option_text": "Delete",
                            "option_value": [
                                "s3:DeleteObject",
                                "s3:DeleteObjectTagging",
                                "s3:DeleteObjectVersion",
                                "s3:DeleteObjectVersionTagging",
                            ],
                        },
                    ],
                ),
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
          "Action": ["{{form.s3_permissions|join('","')}}"],
          "Effect":"Allow",
          "Resource": [{% for s3_bucket in form.s3_buckets %}"{{ s3_bucket }}", "{{ s3_bucket }}/*"{% if not loop.last %}, {% endif %}{% endfor %}]
        }"""
            ),
            supported_template_types=[
                AWS_IAM_GROUP_TEMPLATE_TYPE,
                AWS_IAM_ROLE_TEMPLATE_TYPE,
                AWS_IAM_USER_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        ),
        ChangeType(
            name="SQS",
            description="Request permissions for consuming and publishing to an SQS queue.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="sqs_queues",
                    field_type="TypeAhead",
                    field_text="SQS Queue",
                    description="The SQS Queue the resource requires permissions to. "
                    "You must provide the full ARN. Wildcards supported.",
                    allow_none=False,
                    allow_multiple=True,
                    typeahead_field_helper_id=field_helper_map["SQS Queue ARN"].id,
                ),
                ChangeField(
                    change_element=1,
                    field_key="sqs_permissions",
                    field_type="Choice",
                    field_text="Permission Options",
                    description="The SQS permissions to add",
                    allow_none=False,
                    allow_multiple=True,
                    options=[
                        {
                            "option_text": "Send Message (Queue Producer)",
                            "option_value": [
                                "sqs:GetQueueAttributes",
                                "sqs:GetQueueUrl",
                                "sqs:SendMessage",
                            ],
                        },
                        {
                            "option_text": "Receive/Delete Messages (Queue Consumer)",
                            "option_value": [
                                "sqs:GetQueueAttributes",
                                "sqs:GetQueueUrl",
                                "sqs:ReceiveMessage",
                                "sqs:DeleteMessage",
                                "sqs:ChangeMessageVisibility",
                            ],
                        },
                        {
                            "option_text": "Set Queue Attributes",
                            "option_value": ["sqs:SetQueueAttributes"],
                        },
                        {
                            "option_text": "Purge Queue (You monster!)",
                            "option_value": ["sqs:PurgeQueue"],
                        },
                    ],
                ),
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
          "Action": ["{{form.sqs_permissions|join('","')}}"],
          "Effect":"Allow",
          "Resource": ["{{form.sqs_queues|join('","')}}"]
        }"""
            ),
            supported_template_types=[
                AWS_IAM_GROUP_TEMPLATE_TYPE,
                AWS_IAM_ROLE_TEMPLATE_TYPE,
                AWS_IAM_USER_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        ),
        ChangeType(
            name="SNS",
            description="Request permissions for publishing and subscribing to an SNS topic.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="sns_topics",
                    field_type="TypeAhead",
                    field_text="SNS Topic",
                    description="The SNS Topic the resource requires permissions to. "
                    "You must provide the full ARN. Wildcards supported.",
                    allow_none=False,
                    allow_multiple=False,
                    typeahead_field_helper_id=field_helper_map["SNS Topic ARN"].id,
                ),
                ChangeField(
                    change_element=1,
                    field_key="sns_permissions",
                    field_type="Choice",
                    field_text="Permission Options",
                    description="The SNS permissions to add",
                    allow_none=False,
                    allow_multiple=True,
                    options=[
                        {
                            "option_text": "Get Topic Attributes",
                            "option_value": [
                                "sns:GetEndpointAttributes",
                                "sns:GetTopicAttributes",
                            ],
                        },
                        {"option_text": "Publish", "option_value": ["sns:Publish"]},
                        {
                            "option_text": "Subscribe",
                            "option_value": [
                                "sns:Subscribe",
                                "sns:ConfirmSubscription",
                            ],
                        },
                        {
                            "option_text": "Unsubscribe",
                            "option_value": ["sns:Unsubscribe"],
                        },
                    ],
                ),
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
          "Action": ["{{form.sns_permissions|join('","')}}"],
          "Effect":"Allow",
          "Resource": ["{{form.sns_topics|join('","')}}"]
        }"""
            ),
            supported_template_types=[
                AWS_IAM_GROUP_TEMPLATE_TYPE,
                AWS_IAM_ROLE_TEMPLATE_TYPE,
                AWS_IAM_USER_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        ),
    ]

    already_supported_service_check = [
        f"({change_type.name.lower()}" for change_type in permission_changes
    ]
    for service_name, access_level_data in get_services_permissions().items():
        if any(
            [check in service_name.lower() for check in already_supported_service_check]
        ):
            continue

        options = []
        for access_level, permissions in access_level_data.items():
            options.append(
                {
                    "option_text": access_level,
                    "option_value": permissions,
                }
            )
        permission_changes.append(
            ChangeType(
                name=service_name,
                description=f"Request permissions to a {service_name} resource.",
                change_fields=[
                    ChangeField(
                        change_element=0,
                        field_key="resource_arns",
                        field_type="TextBox",
                        field_text="Resource ARN",
                        description="The Resource ARN the selected identity requires permissions to. "
                        "You must provide the full ARN. Wildcards supported.",
                        allow_none=False,
                        allow_multiple=True,
                    ),
                    ChangeField(
                        change_element=1,
                        field_key="service_permissions",
                        field_type="Choice",
                        field_text="Permission Options",
                        description="The permissions to add",
                        allow_none=False,
                        allow_multiple=True,
                        options=options,
                    ),
                ],
                change_template=ChangeTypeTemplate(
                    template="""
        {
          "Action": ["{{form.service_permissions|join('","')}}"],
          "Effect":"Allow",
          "Resource": ["{{form.resource_arns|join('","')}}"]
        }"""
                ),
                supported_template_types=[
                    AWS_IAM_GROUP_TEMPLATE_TYPE,
                    AWS_IAM_ROLE_TEMPLATE_TYPE,
                    AWS_IAM_USER_TEMPLATE_TYPE,
                ],
                created_by="Noq",
            )
        )

    add_permission_to_identity_request = RequestType(
        name="I need cloud permissions.",
        description="I need permissions to a cloud resource for myself, an Application, or a Managed Policy.",
        provider=aws_provider_resolver.provider,
        created_by="Noq",
    )
    add_permission_to_identity_request.change_types = deepcopy(permission_changes)
    for elem, change_type in enumerate(add_permission_to_identity_request.change_types):
        change_type.template_attribute = "properties.inline_policies"
        change_type.apply_attr_behavior = "Append"
        change_type.provider_definition_field = "Allow Multiple"

        for change_field in change_type.change_fields:
            change_field.change_element += 1
        change_type.change_fields.append(
            ChangeField(
                change_element=0,
                field_key="policy_name",
                field_type="TextBox",
                field_text="Policy Name",
                description="The name of the policy to be created containing the requested permissions.",
                allow_none=False,
                allow_multiple=False,
            )
        )

        init_template = change_type.change_template.template.replace("\n", "\n    ")
        template = f"""
        {{
          "PolicyName": "{{{{form.policy_name}}}}",
          "Statement":[{init_template}
          ],
          "Version":"2012-10-17"
        }}"""
        add_permission_to_identity_request.change_types[
            elem
        ].change_template.template = template

    permission_set_change_types = deepcopy(permission_changes)
    for elem, change_type in enumerate(permission_set_change_types):
        change_type.supported_template_types = [
            AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE
        ]
        change_type.template_attribute = "properties.inline_policy"
        change_type.apply_attr_behavior = "Append"
        change_type.provider_definition_field = "Allow None"
        permission_set_change_types[elem] = change_type
    add_permission_to_identity_request.change_types.extend(permission_set_change_types)

    mp_change_types = deepcopy(permission_changes)
    for elem, change_type in enumerate(mp_change_types):
        change_type.supported_template_types = [AWS_MANAGED_POLICY_TEMPLATE_TYPE]
        change_type.template_attribute = "properties.policy_document.statement"
        change_type.apply_attr_behavior = "Append"
        change_type.provider_definition_field = "Allow Multiple"
        mp_change_types[elem] = change_type
    add_permission_to_identity_request.change_types.extend(mp_change_types)

    add_permission_to_identity_request.change_types.extend(
        [
            ChangeType(
                name="Attach a customer managed policy to a permission set",
                description="Attach a customer managed policy to a permission set",
                change_fields=[
                    ChangeField(
                        change_element=0,
                        field_key="policy",
                        field_type="TypeAheadTemplateRef",
                        field_text="Managed Policy",
                        description="The managed policy that will be attached/added to the permission set.",
                        allow_none=False,
                        allow_multiple=False,
                        typeahead_field_helper_id=field_helper_map[
                            "Customer Managed Policy Template Refs"
                        ].id,
                    )
                ],
                change_template=ChangeTypeTemplate(
                    template="""
        {
            "name": "{{ form.policy.properties.policy_name }}",
            "path": "{{ form.policy.properties.path }}"
        }"""
                ),
                template_attribute="properties.customer_managed_policy_references",
                apply_attr_behavior="Append",
                provider_definition_field="Allow None",
                supported_template_types=[
                    AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
                ],
                created_by="Noq",
            ),
            ChangeType(
                name="Attach an AWS managed policy to a permission set",
                description="Attach a policy managed by AWS to a permission set",
                change_fields=[
                    ChangeField(
                        change_element=0,
                        field_key="policy_arn",
                        field_type="TypeAhead",
                        field_text="Managed Policy",
                        description="The managed policy that will be attached/added to the permission set.",
                        allow_none=False,
                        allow_multiple=False,
                        typeahead_field_helper_id=field_helper_map[
                            "AWS only Managed Policies"
                        ].id,
                    )
                ],
                change_template=ChangeTypeTemplate(
                    template="""
        {
            "arn": "{{ form.policy_arn }}"
        }"""
                ),
                template_attribute="properties.managed_policies",
                apply_attr_behavior="Append",
                provider_definition_field="Allow None",
                supported_template_types=[
                    AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
                ],
                created_by="Noq",
            ),
        ]
    )
    add_permission_to_identity_request.change_types.append(
        ChangeType(
            name="Attach a managed policy",
            description="Attach a managed policy.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="policy_arn",
                    field_type="TypeAhead",
                    field_text="Managed Policy",
                    description="The managed policy that will be attached/added.",
                    allow_none=False,
                    allow_multiple=False,
                    typeahead_field_helper_id=field_helper_map[
                        "AWS and Customer Managed Policies"
                    ].id,
                )
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
            "policy_arn": "{{ form.policy_arn }}"
        }"""
            ),
            template_attribute="properties.managed_policies",
            apply_attr_behavior="Append",
            provider_definition_field="Allow One",
            supported_template_types=[
                AWS_IAM_ROLE_TEMPLATE_TYPE,
                AWS_IAM_USER_TEMPLATE_TYPE,
                AWS_IAM_GROUP_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        )
    )

    return add_permission_to_identity_request


def _get_default_aws_request_access_request_types(
    field_helper_map: dict[str:TypeAheadFieldHelper],
) -> RequestType:

    access_to_aws_request = RequestType(
        name="I need access.",
        description="I do not have the AWS credentials to do my job.",
        provider=aws_provider_resolver.provider,
        created_by="Noq",
    )
    access_to_aws_request.change_types = [
        ChangeType(
            name="Noq User access request",
            description="Request Noq User access to an AWS IAM Role.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="noq_email",
                    field_type="TypeAhead",
                    field_text="User E-Mail",
                    description="The Noq user that requires access.",
                    allow_none=False,
                    allow_multiple=False,
                    typeahead_field_helper_id=field_helper_map["Noq User"].id,
                )
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
            "users":["{{form.noq_email}}"],
            "included_accounts": ["{{form.provider_definitions|join('","')}}"]
        }"""
            ),
            template_attribute="access_rules",
            apply_attr_behavior="Append",
            provider_definition_field="Allow Multiple",
            supported_template_types=[
                AWS_IAM_ROLE_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        ),
        ChangeType(
            name="Noq Group access request",
            description="Request Noq Group access to an AWS IAM Role.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="noq_group",
                    field_type="TypeAhead",
                    field_text="Group",
                    description="The Noq group that requires access.",
                    allow_none=False,
                    allow_multiple=False,
                    typeahead_field_helper_id=field_helper_map["Noq Group"].id,
                )
            ],
            change_template=ChangeTypeTemplate(
                template="""
        {
            "groups":["{{form.noq_group}}"],
            "included_accounts": ["{{form.provider_definitions|join('","')}}"]
        }"""
            ),
            template_attribute="access_rules",
            apply_attr_behavior="Append",
            provider_definition_field="Allow Multiple",
            supported_template_types=[
                AWS_IAM_ROLE_TEMPLATE_TYPE,
            ],
            created_by="Noq",
        ),
    ]

    access_to_aws_request.change_types.extend(
        [
            ChangeType(
                name="SSO User access request",
                description="Request SSO User access to an AWS SSO PermissionSet.",
                change_fields=[
                    ChangeField(
                        change_element=0,
                        field_key="sso_username",
                        field_type="TextBox",
                        field_text="User",
                        description="The SSO user that requires access.",
                        allow_none=False,
                        allow_multiple=False,
                    )
                ],
                change_template=ChangeTypeTemplate(
                    template="""
        {
            "users":["{{form.sso_username}}"],
            "included_accounts": ["{{form.provider_definitions|join('","')}}"]
        }"""
                ),
                template_attribute="access_rules",
                apply_attr_behavior="Append",
                provider_definition_field="Allow Multiple",
                supported_template_types=[
                    AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
                ],
                created_by="Noq",
            ),
            ChangeType(
                name="SSO Group access request",
                description="Request SSO Group access to an AWS SSO PermissionSet.",
                change_fields=[
                    ChangeField(
                        change_element=0,
                        field_key="sso_group",
                        field_type="TextBox",
                        field_text="Group",
                        description="The SSO group that requires access.",
                        allow_none=False,
                        allow_multiple=False,
                    )
                ],
                change_template=ChangeTypeTemplate(
                    template="""
        {
            "groups":["{{form.sso_group}}"],
            "included_accounts": ["{{form.provider_definitions|join('","')}}"]
        }"""
                ),
                template_attribute="access_rules",
                apply_attr_behavior="Append",
                provider_definition_field="Allow Multiple",
                supported_template_types=[
                    AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
                ],
                created_by="Noq",
            ),
        ]
    )

    return access_to_aws_request


async def get_default_aws_request_types() -> list[RequestType]:
    aws_typeahead_field_helpers = await list_provider_typeahead_field_helpers(
        provider=aws_provider_resolver.provider
    )
    field_helper_map = {
        field_helper.name: field_helper for field_helper in aws_typeahead_field_helpers
    }
    default_request_types = [
        _get_default_aws_request_permission_request_types(field_helper_map),
        _get_default_aws_request_access_request_types(field_helper_map),
    ]

    return [deepcopy(request_type) for request_type in default_request_types]
