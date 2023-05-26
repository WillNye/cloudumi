from copy import deepcopy

from iambic.plugins.v0_1_0.aws.iam.group.models import AWS_IAM_GROUP_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.policy.models import AWS_MANAGED_POLICY_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.role.models import AWS_IAM_ROLE_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.iam.user.models import AWS_IAM_USER_TEMPLATE_TYPE
from iambic.plugins.v0_1_0.aws.identity_center.permission_set.models import (
    AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
)

from common.iambic.config.models import TRUSTED_PROVIDER_RESOLVER_MAP
from common.request_types.models import (
    ChangeField,
    ChangeType,
    ChangeTypeTemplate,
    RequestType,
)
from common.request_types.utils import list_provider_typeahead_field_helpers

aws_provider_resolver = TRUSTED_PROVIDER_RESOLVER_MAP["aws"]


async def get_default_aws_request_types() -> list[RequestType]:
    aws_typeahead_field_helpers = await list_provider_typeahead_field_helpers(
        provider=aws_provider_resolver.provider
    )
    field_helper_map = {
        field_helper.name: field_helper for field_helper in aws_typeahead_field_helpers
    }

    permission_changes = [
        ChangeType(
            name="S3",
            description="Add S3 permissions",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="s3_bucket",
                    field_type="TypeAhead",
                    field_text="S3 Bucket",
                    description="The S3 bucket the resource requires permissions to. "
                    "You must provide the full ARN.",
                    allow_none=False,
                    allow_multiple=False,
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
      "Statement":[
        {
          "Action":{{form.s3_permissions}},
          "Effect":"Allow",
          "Resource": ["{{form.s3_bucket}}","{{form.s3_bucket}}/*"]}
      ],
      "Version":"2012-10-17"
    }"""
            ),
            created_by="Noq",
        ),
        ChangeType(
            name="SQS",
            description="Request permissions for consuming and publishing to an SQS queue.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="sqs_queue",
                    field_type="TypeAhead",
                    field_text="SQS Queue",
                    description="The SQS Queue the resource requires permissions to. "
                    "You must provide the full ARN.",
                    allow_none=False,
                    allow_multiple=False,
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
      "Statement":[
        {
          "Action": {{form.sqs_permissions}},
          "Effect":"Allow",
          "Resource": ["{{form.sqs_queue}}"]
        }
      ],
      "Version":"2012-10-17"
    }"""
            ),
            created_by="Noq",
        ),
        ChangeType(
            name="SNS",
            description="Request permissions for publishing and subscribing to an SNS topic.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="sns_topic",
                    field_type="TypeAhead",
                    field_text="SNS Topic",
                    description="The SNS Topic the resource requires permissions to. "
                    "You must provide the full ARN.",
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
      "Statement":[
        {
          "Action": {{form.sns_permissions}},
          "Effect":"Allow",
          "Resource": ["{{form.sns_topic}}"]
        }
      ],
      "Version":"2012-10-17"
    }"""
            ),
            created_by="Noq",
        ),
        ChangeType(
            name="RDS",
            description="Request permissions to an RDS resource.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="rds_resource_arn",
                    field_type="TextBox",
                    field_text="RDS Resource ARN",
                    description="The RDS Resource ARN the selected identity requires permissions to. "
                    "You must provide the full ARN.",
                    allow_none=False,
                    allow_multiple=False,
                ),
                ChangeField(
                    change_element=1,
                    field_key="rds_permissions",
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
      "Statement":[
        {
          "Action": {{form.rds_permissions}},
          "Effect":"Allow",
          "Resource": ["{{form.rds_resource_arn}}"]
        }
      ],
      "Version":"2012-10-17"
    }"""
            ),
            created_by="Noq",
        ),
        ChangeType(
            name="Other",
            description="Request permissions to a service not on the list.",
            change_fields=[
                ChangeField(
                    change_element=0,
                    field_key="service_name",
                    field_type="TypeAhead",
                    field_text="Service Name",
                    description="The resources service type the selected identity requires permissions to. ",
                    allow_none=False,
                    allow_multiple=False,
                ),
                ChangeField(
                    change_element=1,
                    field_key="resource_arn",
                    field_type="TextBox",
                    field_text="Resource ARN",
                    description="The Resource ARN the selected identity requires permissions to. "
                    "You must provide the full ARN.",
                    allow_none=False,
                    allow_multiple=False,
                ),
                ChangeField(
                    change_element=2,
                    field_key="service_permissions",
                    field_type="CallbackChoice",
                    field_text="Permission Options",
                    description="The permissions to add",
                    allow_none=False,
                    allow_multiple=True,
                    options=[
                        {
                            "option_text": "Write",
                            "option_value": "/api/v4/aws/services/{{form.service_name}}/permissions/Write",
                        },
                        {
                            "option_text": "Read",
                            "option_value": "/api/v4/aws/services/{{form.service_name}}/permissions/Read",
                        },
                        {
                            "option_text": "List",
                            "option_value": "/api/v4/aws/services/{{form.service_name}}/permissions/List",
                        },
                        {
                            "option_text": "Tagging",
                            "option_value": "/api/v4/aws/services/{{form.service_name}}/permissions/Tagging",
                        },
                        {
                            "option_text": "Permissions management",
                            "option_value": "/api/v4/aws/services/{{form.service_name}}/permissions/Permissions+management",
                        },
                    ],
                ),
            ],
            change_template=ChangeTypeTemplate(
                template="""
    {
        "Statement":[
            {
                "Action": {{form.service_permissions}},
                "Effect":"Allow",
                "Resource": ["{{form.resource_arn}}"]
            }
        ],
        "Version":"2012-10-17"
    }"""
            ),
            created_by="Noq",
        ),
    ]

    add_permission_to_identity_request = RequestType(
        name="Add permissions to identity",
        description="Add permissions to an identity on 1 or more accounts",
        provider=aws_provider_resolver.provider,
        template_types=[
            AWS_IAM_GROUP_TEMPLATE_TYPE,
            AWS_IAM_ROLE_TEMPLATE_TYPE,
            AWS_IAM_USER_TEMPLATE_TYPE,
            AWS_IDENTITY_CENTER_PERMISSION_SET_TEMPLATE_TYPE,
        ],
        template_attribute="properties.inline_policies",
        apply_attr_behavior="Append",
        created_by="Noq",
    )
    add_permission_to_identity_request.change_types = deepcopy(permission_changes)

    add_permission_to_mp_request = RequestType(
        name="Add permissions to managed policy",
        description="Add permissions to a managed policy on 1 or more accounts",
        provider=aws_provider_resolver.provider,
        template_types=[AWS_MANAGED_POLICY_TEMPLATE_TYPE],
        template_attribute="properties.policy_document",
        apply_attr_behavior="Merge",
        created_by="Noq",
    )
    add_permission_to_mp_request.change_types = deepcopy(permission_changes)

    return [add_permission_to_identity_request, add_permission_to_mp_request]


"""

['Write', 'Read', 'List', 'Tagging', 'Permissions management']

"""
