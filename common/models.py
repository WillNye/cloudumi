# generated by datamodel-codegen:
#   filename:  swagger.yaml
#   timestamp: 2022-04-20T15:45:53+00:00

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import Field, constr

from common.lib.pydantic import BaseModel


class ActionResult(BaseModel):
    status: Optional[str] = None
    message: Optional[str] = None


class Action(Enum):
    attach = "attach"
    detach = "detach"


class ResourceModel(BaseModel):
    arn: str = Field(..., description="resource ARN")
    name: str = Field(..., description="Resource Name")
    account_id: Optional[str] = Field(None, description="AWS account ID")
    region: Optional[str] = Field(None, description="Region")
    account_name: Optional[str] = Field(
        None, description="human-friendly AWS account name"
    )
    policy_sha256: Optional[str] = Field(
        None, description="hash of the most recent resource policy seen by ConsoleMe"
    )
    policy: Optional[str] = None
    actions: Optional[List[str]] = None
    owner: Optional[str] = Field(
        None, description="email address of team or individual who owns this resource"
    )
    approvers: Optional[List[str]] = None
    resource_type: str
    last_updated: Optional[datetime] = Field(
        None, description="last time resource was updated from source-of-truth"
    )


class RequestStatus(Enum):
    pending = "pending"
    cancelled = "cancelled"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class GeneratorType(Enum):
    advanced = "advanced"
    crud_lookup = "crud_lookup"
    ec2 = "ec2"
    generic = "generic"
    rds = "rds"
    route53 = "route53"
    s3 = "s3"
    ses = "ses"
    sns = "sns"
    sqs = "sqs"
    sts = "sts"
    custom_iam = "custom_iam"


class PrincipalType(Enum):
    AwsResource = "AwsResource"
    HoneybeeAwsResourceTemplate = "HoneybeeAwsResourceTemplate"
    TerraformAwsResource = "TerraformAwsResource"


class PrincipalModel(BaseModel):
    principal_type: PrincipalType


class AwsResourcePrincipalModel(PrincipalModel):
    principal_type: constr(regex=r"AwsResource")
    principal_arn: constr(
        regex=r"(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    ) = Field(
        ...,
        description="The principal (Source ARN) associated with the Change. This is most commomly an IAM role ARN.\nThe principal ARN is associated with the entity whose policy will be modified if the change is\napproved and successful.",
        example="arn:aws:iam::123456789012:role/exampleRole",
    )


class TerraformAwsResourcePrincipalModel(PrincipalModel):
    principal_type: constr(regex=r"TerraformAwsResource")
    repository_name: str = Field(
        ...,
        description="The name of the repository for the template. This is specified in the configuration key\n`cache_resource_templates.repositories[n].name`",
    )
    resource_identifier: str = Field(..., example="path/to/template.tf")
    resource_url: str = Field(..., example="https://example.com/resource.tf")
    file_path: Optional[str] = Field(None, example="path/to/template.tf")


class HoneybeeAwsResourceTemplatePrincipalModel(PrincipalModel):
    principal_type: constr(regex=r"HoneybeeAwsResourceTemplate")
    repository_name: str = Field(
        ...,
        description="The name of the repository for the template. This is specified in the configuration key\n`cache_resource_templates.repositories[n].name`",
    )
    resource_identifier: str = Field(..., example="path/to/template.yaml")
    resource_url: str = Field(..., example="https://example.com/resource")


class Status(Enum):
    applied = "applied"
    not_applied = "not_applied"
    cancelled = "cancelled"
    expired = "expired"


class ChangeModel(BaseModel):
    principal: Union[
        AwsResourcePrincipalModel,
        HoneybeeAwsResourceTemplatePrincipalModel,
        TerraformAwsResourcePrincipalModel,
    ]
    change_type: str
    resources: Optional[List[ResourceModel]] = []
    version: Optional[str] = 3.0
    status: Optional[Status] = "not_applied"
    id: Optional[str] = None
    autogenerated: Optional[bool] = False
    updated_by: Optional[str] = None


class Encoding(Enum):
    yaml = "yaml"
    json = "json"
    hcl = "hcl"
    text = "text"


class GenericFileChangeModel(ChangeModel):
    principal: Optional[
        Union[
            AwsResourcePrincipalModel,
            HoneybeeAwsResourceTemplatePrincipalModel,
            TerraformAwsResourcePrincipalModel,
        ]
    ] = None
    action: Optional[Action] = None
    change_type: Optional[constr(regex=r"generic_file")] = None
    policy: Optional[str] = None
    old_policy: Optional[str] = None
    encoding: Optional[Encoding] = None


class TagAction(Enum):
    create = "create"
    update = "update"
    delete = "delete"


class ResourceTagChangeModel(ChangeModel):
    original_key: Optional[str] = Field(
        None,
        description="original_key is used for renaming a key to something else. This is optional.",
        example="key_to_be_renamed",
    )
    key: Optional[str] = Field(
        None,
        description="This is the desired key name for the tag. If a tag key is being renamed, this is what it will be renamed\nto. Otherwise, this key name will be used when creating or updating a tag.",
        example="desired_key_name",
    )
    original_value: Optional[str] = None
    value: Optional[str] = None
    change_type: Optional[constr(regex=r"resource_tag")] = None
    tag_action: TagAction


class ManagedPolicyChangeModel(ChangeModel):
    arn: constr(
        regex=r"(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    )
    change_type: Optional[constr(regex=r"managed_policy")] = None
    action: Action


class PermissionsBoundaryChangeModel(ChangeModel):
    arn: constr(
        regex=r"(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    )
    change_type: Optional[constr(regex=r"permissions_boundary")] = None
    action: Action


class ArnArray(BaseModel):
    __root__: List[
        constr(
            regex=r"^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$"
        )
    ]


class Status1(Enum):
    active = "active"
    in_progress = "in-progress"
    in_active = "in-active"
    deleted = "deleted"
    created = "created"
    suspended = "suspended"
    deprecated = "deprecated"


class Type(Enum):
    aws = "aws"
    gcp = "gcp"


class Environment(Enum):
    prod = "prod"
    test = "test"


class CloudAccountModel(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[Status1] = None
    type: Optional[Type] = None
    sync_enabled: Optional[bool] = None
    sensitive: Optional[bool] = False
    environment: Optional[Environment] = None
    aliases: Optional[List[str]] = None
    email: Optional[str] = None


class PolicyModel(BaseModel):
    version: Optional[str] = Field(None, description="AWS Policy Version")
    policy_document: Optional[Dict[str, Any]] = Field(
        None, description="JSON policy document"
    )
    policy_sha256: Optional[str] = Field(
        None, description="hash of the policy_document json"
    )


class PolicyStatement(BaseModel):
    action: List[str] = Field(..., description="AWS Policy Actions")
    effect: str = Field(..., description="Allow | Deny")
    resource: List[str] = Field(..., description="AWS Resource ARNs")
    sid: Optional[constr(regex=r"^([a-zA-Z0-9]+)*")] = Field(
        None, description="Statement identifier"
    )


class AwsPrincipalModel(BaseModel):
    name: str = Field(..., example="super_awesome_admin")
    account_id: constr(min_length=12, max_length=12) = Field(
        ..., example="123456789012"
    )
    account_name: Optional[str] = Field(None, example="super_awesome")
    arn: Optional[
        constr(
            regex=r"(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
        )
    ] = Field(None, example="arn:aws:iam::123456789012:role/super_awesome_admin")


class CloudTrailError(BaseModel):
    event_call: Optional[str] = Field(None, example="sqs:CreateQueue")
    resource: Optional[str] = Field(
        None, example="arn:aws:iam::123456789012:role/roleName"
    )
    generated_policy: Optional[Dict[str, Any]] = Field(
        None,
        example={
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Resource": ["arn:aws:iam::123456789012:role/roleName"],
                    "Action": ["sts:AssumeRole"],
                    "Effect": "Allow",
                }
            ],
        },
    )
    count: Optional[int] = Field(None, example=5)


class CloudTrailErrorArray(BaseModel):
    cloudtrail_errors: Optional[List[CloudTrailError]] = None


class CloudTrailDetailsModel(BaseModel):
    error_url: Optional[str] = Field(
        None, example="https://cloudtrail_logs/for/role_arn"
    )
    errors: Optional[CloudTrailErrorArray] = None


class S3Error(BaseModel):
    error_call: Optional[str] = Field(None, example="s3:PutObject")
    count: Optional[int] = Field(None, example=5)
    bucket_name: Optional[str] = Field(None, example="bucket_name")
    request_prefix: Optional[str] = Field(None, example="folder/file.txt")
    status_code: Optional[int] = Field(None, example=403)
    status_text: Optional[str] = Field(None, example="AccessDenied")
    role_arn: Optional[
        constr(
            regex=r"(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
        )
    ] = Field(None, example="arn:aws:iam::123456789012:role/roleName")


class S3ErrorArray(BaseModel):
    s3_errors: Optional[List[S3Error]] = None


class S3DetailsModel(BaseModel):
    query_url: Optional[str] = Field(
        None, example="https://s3_log_query/for/role_or_bucket_arn"
    )
    error_url: Optional[str] = Field(
        None, example="https://s3_error_query/for/role_or_bucket_arn"
    )
    errors: Optional[S3ErrorArray] = None


class AppDetailsModel(BaseModel):
    name: Optional[str] = Field(None, example="app_name")
    owner: Optional[str] = Field(None, example="owner@example.com")
    owner_url: Optional[str] = Field(None, example="https://link_to_owner_group")
    app_url: Optional[str] = Field(
        None, example="https://link_to_app_ci_pipeline_for_app"
    )


class AppDetailsArray(BaseModel):
    app_details: Optional[List[AppDetailsModel]] = None


class ExtendedAwsPrincipalModel(AwsPrincipalModel):
    inline_policies: List[Dict[str, Any]]
    assume_role_policy_document: Optional[Dict[str, Any]] = None
    cloudtrail_details: Optional[CloudTrailDetailsModel] = None
    s3_details: Optional[S3DetailsModel] = None
    apps: Optional[AppDetailsArray] = None
    managed_policies: List[Dict[str, Any]]
    permissions_boundary: Optional[Dict[str, Any]] = None
    tags: List[Dict[str, Any]]
    effective_policy: Optional[Dict[str, Any]] = Field(
        None,
        description='"The minified effective policy for the principal. This is effectively a combination "\n"of the inline policies and managed policies of the principal. "',
    )
    effective_policy_repoed: Optional[Dict[str, Any]] = Field(
        None,
        description='"The minified effective policy for the principal, with unused permissions removed."',
    )
    config_timeline_url: Optional[str] = Field(
        None, description="A link to the role's AWS Config Timeline"
    )
    templated: Optional[bool] = None
    template_link: Optional[str] = None
    created_time: Optional[str] = None
    updated_time: Optional[str] = None
    last_used_time: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = Field(
        None,
        description="A string depicting the owning user or group for a given AWS principal. Typically determined by one or\nmore tags on the principal.",
    )


class UserModel(BaseModel):
    email: Optional[str] = None
    extended_info: Optional[Dict[str, Any]] = None
    details_url: Optional[str] = Field(None, example="https://details_about/user")
    photo_url: Optional[str] = Field(
        None, example="https://user_photos/user_thumbnail.jpg"
    )


class ApiErrorModel(BaseModel):
    status: Optional[int] = None
    title: Optional[str] = None
    message: Optional[str] = None


class Options(BaseModel):
    assume_role_policy: Optional[bool] = False
    tags: Optional[bool] = False
    copy_description: Optional[bool] = False
    description: Optional[str] = None
    inline_policies: Optional[bool] = False
    managed_policies: Optional[bool] = False
    max_session_duration: Optional[bool] = False


class CloneRoleRequestModel(BaseModel):
    account_id: constr(min_length=12, max_length=12)
    role_name: str
    dest_account_id: constr(min_length=12, max_length=12)
    dest_role_name: str
    options: Options


class CreateCloneRequestResponse(BaseModel):
    errors: Optional[int] = None
    role_created: Optional[bool] = None
    action_results: Optional[List[ActionResult]] = None


class RoleCreationRequestModel(BaseModel):
    account_id: constr(min_length=12, max_length=12)
    role_name: str
    description: Optional[str] = None
    instance_profile: Optional[bool] = True


class Command(Enum):
    add_comment = "add_comment"
    approve_request = "approve_request"
    reject_request = "reject_request"
    cancel_request = "cancel_request"
    apply_change = "apply_change"
    update_change = "update_change"
    cancel_change = "cancel_change"
    move_back_to_pending = "move_back_to_pending"
    update_expiration_date = "update_expiration_date"


class RequestModificationBaseModel(BaseModel):
    command: Command


class ExpirationDateRequestModificationModel(RequestModificationBaseModel):
    expiration_date: Optional[int] = Field(
        ...,
        description="Date to expire requested policy, in the format of YYYYmmdd",
        example=20210905,
    )


class CommentRequestModificationModel(RequestModificationBaseModel):
    comment_text: str


class UpdateChangeModificationModel(RequestModificationBaseModel):
    policy_document: Dict[str, Any]
    change_id: str


class ApplyChangeModificationModel(RequestModificationBaseModel):
    policy_document: Optional[Dict[str, Any]] = None
    change_id: str


class CancelChangeModificationModel(RequestModificationBaseModel):
    policy_document: Optional[Dict[str, Any]] = None
    change_id: str


class ChangeRequestStatusModificationModel(RequestModificationBaseModel):
    pass


class MoveToPendingRequestModificationModel(RequestModificationBaseModel):
    pass


class PolicyRequestChange(BaseModel):
    policy_document: Dict[str, Any]
    change_id: str


class ApproveRequestModificationModel(RequestModificationBaseModel):
    policy_request_changes: Optional[List[PolicyRequestChange]] = None


class PolicyRequestModificationRequestModel(BaseModel):
    modification_model: Union[
        CommentRequestModificationModel,
        UpdateChangeModificationModel,
        ExpirationDateRequestModificationModel,
        ApplyChangeModificationModel,
        ApproveRequestModificationModel,
        MoveToPendingRequestModificationModel,
        ChangeRequestStatusModificationModel,
    ]


class ActionResult1(BaseModel):
    status: Optional[str] = None
    message: Optional[str] = None
    visible: Optional[bool] = True


class PolicyRequestModificationResponseModel(BaseModel):
    errors: Optional[int] = None
    action_results: Optional[List[ActionResult1]] = None


class AuthenticationResponse(BaseModel):
    authenticated: Optional[bool] = None
    errors: Optional[List[str]] = None
    username: Optional[str] = None
    groups: Optional[List[str]] = None


class UserManagementAction(Enum):
    create = "create"
    update = "update"
    delete = "delete"


class UserManagementModel(BaseModel):
    user_management_action: Optional[UserManagementAction] = None
    username: Optional[str] = None
    password: Optional[str] = None
    groups: Optional[List[str]] = None


class LoginAttemptModel(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    after_redirect_uri: Optional[str] = None


class RegistrationAttemptModel(BaseModel):
    username: str
    password: str


class Status2(Enum):
    success = "success"
    error = "error"
    redirect = "redirect"


class WebResponse(BaseModel):
    status: Optional[Status2] = None
    reason: Optional[str] = Field(
        None,
        example=["authenticated_redirect", "authentication_failure", "not_configured"],
    )
    redirect_url: Optional[str] = None
    status_code: Optional[int] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None
    count: Optional[int] = None
    total: Optional[int] = None
    page: Optional[int] = None
    last_page: Optional[int] = None
    data: Optional[Union[Dict[str, Any], List]] = None


class DataTableResponse(BaseModel):
    totalCount: int
    filteredCount: int
    data: List[Dict[str, Any]]


class PolicyCheckModelItem(BaseModel):
    issue: Optional[str] = None
    detail: Optional[str] = None
    location: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class PolicyCheckModel(BaseModel):
    __root__: List[PolicyCheckModelItem]


class ServiceControlPolicyDetailsModel(BaseModel):
    id: str
    arn: str
    name: str
    description: str
    type: Optional[str] = None
    aws_managed: bool
    content: str


class ServiceControlPolicyTargetModel(BaseModel):
    target_id: str
    arn: str
    name: str
    type: str


class ServiceControlPolicyModel(BaseModel):
    targets: List[ServiceControlPolicyTargetModel]
    policy: ServiceControlPolicyDetailsModel


class ServiceControlPolicyArrayModel(BaseModel):
    __root__: List[ServiceControlPolicyModel]


class EligibleRolesModel(BaseModel):
    arn: str = Field(..., description="ARN of the role")
    account_id: str = Field(..., description="Account ID of the role")
    account_friendly_name: Optional[str] = Field(
        None, description='Account\'s friendly name (if known), otherwise "Unknown"'
    )
    role_name: str = Field(..., description="Name of the role")
    apps: Optional[AppDetailsArray] = None


class EligibleRolesModelArray(BaseModel):
    roles: Optional[List[EligibleRolesModel]] = None


class HubAccount(BaseModel):
    name: str = Field(
        ..., description="Customer-specified or default hub role name (NoqCentralRole)"
    )
    account_name: Optional[str] = Field(None, description="Account name")
    account_id: constr(regex=r"^\d{12}$") = Field(..., description="AWS account id")
    role_arn: Optional[str] = Field(None, description="ARN of the role")
    external_id: Optional[str] = Field(
        None,
        description="Designated external identifier to provide a safeguard against brute force attempts",
    )


class SpokeAccount(BaseModel):
    name: str = Field(
        ..., description="Customer-specified or default spoke role name (NoqSpokeRole)"
    )
    account_name: Optional[str] = Field(None, description="Account name")
    account_id: constr(regex=r"^\d{12}$") = Field(..., description="AWS account id")
    role_arn: Optional[str] = Field(None, description="ARN of the spoke role")
    external_id: Optional[str] = Field(
        None,
        description="Designated external identifier to provide a safeguard against brute force attempts",
    )
    hub_account_arn: Optional[str] = Field(
        None, description="Links to the designated hub role ARN"
    )
    master_for_account: Optional[bool] = Field(
        False,
        description="Optional value (defaults to false) to indicate whether this spoke role has master access rights on the account",
    )
    owners: Optional[List[str]] = Field(
        [], description="Optional user or group that owns the account"
    )
    viewers: Optional[List[str]] = Field(
        [],
        description="Optional list of users or groups that can view resources for the account",
    )
    delegate_admin_to_owner: Optional[bool] = Field(
        False,
        description="Optional value (defaults to false) to indicate whether the owner should be delegated admin rights for policy requests\non this account. If this is set, the delegated admin will be able to approve policy requests pertaining to this account.",
    )
    restrict_viewers_of_account_resources: Optional[bool] = Field(
        False,
        description="Optional value (defaults to false) to indicate whether to restrict who can view resources from this account in Noq.\nIf this is set, viewers will be restricted to the list of users or groups provided in the `viewers` field.",
    )


class OrgAccount(BaseModel):
    org_id: str = Field(
        ...,
        description="A unique identifier designating the identity of the organization",
    )
    account_id: Optional[constr(regex=r"^\d{12}$")] = Field(
        None, description="AWS account id"
    )
    account_name: Optional[str] = Field(None, description="AWS account name")
    owner: Optional[str] = Field(None, description="AWS account owner")


class GoogleOIDCSSOIDPProvider(BaseModel):
    client_id: str = Field(
        ..., description="A unique client_id to be used for identification"
    )
    client_secret: str = Field(
        ..., description="The client secret used to authenticate to SSO IDP"
    )
    authorize_scopes: str = Field(
        ...,
        description="OpenID Connect Clients use scope values as defined in 3.3 of OAuth 2.0 [RFC6749] to specify what access privileges are being requested for Access Tokens. The scopes associated with Access Tokens determine what resources will be available when they are used to access OAuth 2.0 protected endpoints. For OpenID Connect, scopes can be used to request that specific sets of information be made available as Claim Values. This document describes only the scope values used by OpenID Connect.",
    )
    provider_name: constr(regex=r"^Google$") = Field(
        ..., description="The identity provider name."
    )
    provider_type: constr(regex=r"^Google$") = Field(
        ..., description="The identity provider type."
    )


class SamlOIDCSSOIDPProvider(BaseModel):
    MetadataURL: str = Field(
        ..., description="The metadata defining the SAML authentication"
    )
    provider_name: constr(regex=r"^SAML$") = Field(
        ..., description="The identity provider name."
    )
    provider_type: constr(regex=r"^SAML$") = Field(
        ..., description="The identity provider type."
    )


class OIDCSSOIDPProvider(BaseModel):
    client_id: str = Field(
        ...,
        description="A unique client id used for authentication with OIDC providers",
    )
    client_secret: str = Field(
        ...,
        description="A unique client id used for authentication with OIDC providers",
    )
    attributes_request_method: str = Field(
        ...,
        description="A unique client id used for authentication with OIDC providers",
    )
    oidc_issuer: str = Field(
        ...,
        description="A unique client id used for authentication with OIDC providers",
    )
    authorize_scopes: str = Field(
        ...,
        description="A unique client id used for authentication with OIDC providers",
    )
    authorize_url: Optional[str] = Field(
        None,
        description="if not available from discovery URL specified by oidc_issuer key",
    )
    token_url: Optional[str] = Field(
        None,
        description="if not available from discovery URL specified by oidc_issuer key",
    )
    attributes_url: Optional[str] = Field(
        None,
        description="if not available from discovery URL specified by oidc_issuer key",
    )
    jwks_uri: Optional[str] = Field(
        None,
        description="if not available from discovery URL specified by oidc_issuer key",
    )
    attributes_url_add_attributes: Optional[str] = Field(
        None, description="a read-only property that is set automatically"
    )
    provider_name: constr(regex=r"^OIDC$") = Field(
        ..., description="The identity provider name."
    )
    provider_type: constr(regex=r"^OIDC$") = Field(
        ..., description="The identity provider type."
    )


class SSOIDPProviders(BaseModel):
    google: Optional[GoogleOIDCSSOIDPProvider] = None
    saml: Optional[SamlOIDCSSOIDPProvider] = None
    oidc: Optional[OIDCSSOIDPProvider] = None


class Attribute(BaseModel):
    Name: Optional[str] = Field(
        None,
        description="attribute name - reference https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html#CognitoIdentityProvider.Client.admin_create_user",
    )
    Value: Optional[str] = Field(
        None,
        description="attribute value - reference https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-idp.html#CognitoIdentityProvider.Client.admin_create_user",
    )


class DeliveryMedium(Enum):
    SMS = "SMS"
    EMAIL = "EMAIL"


class MFAOption(BaseModel):
    DeliveryMedium: Optional[DeliveryMedium] = Field(
        None, description="can be either SMS or EMAIL"
    )
    AttributeName: Optional[str] = None


class UserStatus(Enum):
    UNCONFIRMED = "UNCONFIRMED"
    CONFIRMED = "CONFIRMED"
    ARCHIVED = "ARCHIVED"
    COMPROMISED = "COMPROMISED"
    UNKNOWN = "UNKNOWN"
    RESET_REQUIRED = "RESET_REQUIRED"
    FORCE_CHANGE_PASSWORD = "FORCE_CHANGE_PASSWORD"


class CognitoUser(BaseModel):
    Username: str = Field(
        ...,
        description="required - The username for the user. Must be unique within the user pool. Must be a UTF-8 string between 1 and 128 characters. After the user is created, the username can't be changed.",
    )
    Attributes: Optional[List[Attribute]] = None
    Enabled: Optional[bool] = None
    MFAOptions: Optional[List[MFAOption]] = Field(
        None, description="Align with what we get back from cognito list users"
    )
    Groups: Optional[List[str]] = Field(
        None,
        description="assigns Cognito group memberships to user account; these groups *must* exist before they can be assigned",
    )
    UserStatus: Optional[UserStatus] = Field(
        None,
        description="Can be UNCONFIRMED, CONFIRMED, ARCHIVED, COMPROMISED, UNKNOWN, RESET_REQUIRED, FORCE_CHANGE_PASSWORD",
    )


class CognitoGroup(BaseModel):
    GroupName: Optional[str] = Field(
        None, description="required - The name of the group. Must be unique."
    )
    Description: Optional[str] = Field(
        "",
        description="uhm... description is the description, and that is this description of the description",
    )
    RoleArn: Optional[str] = Field(
        None, description="The role Amazon Resource Name (ARN) for the group."
    )


class CognitoAccounts(BaseModel):
    users: Optional[List[CognitoUser]] = None
    groups: Optional[List[CognitoGroup]] = None


class ChallengeUrl(BaseModel):
    enabled: Optional[bool] = Field(
        None, description="Whether CLI authentication via Challenge URL is enabled"
    )


class SlackIntegration(BaseModel):
    enabled: Optional[bool] = Field(
        None, description="Whether the slack webhook is enabled"
    )
    webhook_url: Optional[str] = Field(
        None, description="The slack webhook URL to configure for the callback"
    )


class AutomaticPolicyRequest(BaseModel):
    policy: str = Field(
        ..., description="The json dumped policy requested for approval"
    )
    role: str = Field(
        ...,
        description="The AWS Role arn",
        example="arn:aws:iam::111118675309:role/AutomaticPermissionsRole",
    )


class Status3(Enum):
    approved = "approved"
    applied = "applied"
    pending = "pending"
    denied = "denied"


class ExtendedAutomaticPolicyRequest(BaseModel):
    id: str = Field(..., description="A sha256 hash that represents the policy request")
    role: str = Field(
        ...,
        description="The AWS Role arn",
        example="arn:aws:iam::111118675309:role/AutomaticPermissionsRole",
    )
    account: SpokeAccount
    role_owner: Optional[str] = Field(None, description="The owner of the AWS role")
    user: str = Field(..., description="The AWS user requesting the generated policy")
    event_time: datetime = Field(..., description="The time the request was made")
    error: Optional[str] = Field(
        None, description="The AWS response that caused the automatic policy request"
    )
    system: Optional[str] = Field(
        None, description="The information of the device the request was generated on"
    )
    process: Optional[str] = Field(
        None,
        description="Information about the running process that caused the automatic policy request to be generated",
    )
    policy: Dict[str, Any] = Field(
        ..., description="The json representation of the policy requested for approval"
    )
    status: Optional[Status3] = Field(
        "pending", description="The policy request's status"
    )


class RequestModel(BaseModel):
    id: Optional[str] = None
    request_url: Optional[str] = None
    principal: Union[
        AwsResourcePrincipalModel,
        HoneybeeAwsResourceTemplatePrincipalModel,
        TerraformAwsResourcePrincipalModel,
    ]
    timestamp: datetime
    justification: Optional[str] = None
    requester_email: str
    approvers: List[str] = Field(
        ...,
        description="list of approvers, derived from approvers of `resource`s in `changes`",
    )
    request_status: RequestStatus
    cross_account: Optional[bool] = Field(
        None, description="if true, the request touches cross-account resources"
    )
    arn_url: Optional[str] = Field(None, description="the principal arn's URL")
    admin_auto_approve: Optional[bool] = False


class ChangeGeneratorModel(BaseModel):
    principal: Optional[
        Union[
            AwsResourcePrincipalModel,
            HoneybeeAwsResourceTemplatePrincipalModel,
            TerraformAwsResourcePrincipalModel,
        ]
    ] = None
    generator_type: GeneratorType
    resource_arn: Optional[Union[str, List[str]]] = Field(
        None,
        description="The ARN(s) of the resource being accessed. This is often SQS/SNS/S3/etc. ARNs. It is possible that the\nresource policies will need to be modified if the change is approved and successful.",
        example=[
            "arn:aws:sqs:us-east-1:123456789012:sqs_queue,",
            "arn:aws:sqs:us-west-2:123456789012:sqs_queue2,",
        ],
    )
    version: Optional[str] = Field(2.0, description="Version")
    user: Optional[str] = Field(
        None, description="Email address of user creating the change"
    )
    action_groups: Optional[List[str]] = Field(None, description="Action groups")
    policy_name: Optional[constr(regex=r"^[a-zA-Z0-9+=,.@\\-_]+$")] = Field(
        None, description="Optional policy name for the change, if applicable."
    )
    effect: Optional[constr(regex=r"^(Allow|Deny)$")] = Field(
        "Allow", description="The effect. By default, this is allow"
    )
    condition: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional condition for the change",
        example='{\n    "StringEquals": {"iam:PassedToService": "ec2.amazonaws.com"},\n    "StringLike": {\n        "iam:AssociatedResourceARN": [\n            "arn:aws:ec2:us-east-1:111122223333:instance/*",\n            "arn:aws:ec2:us-west-1:111122223333:instance/*"\n        ]\n    }\n}',
    )
    service: Optional[str] = None
    bucket_prefix: Optional[str] = None
    policy: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional full policy statement provided by frontend",
        example='{\n  "Version": "2012-10-17",\n  "Statement": [\n      {\n          "Action": [\n              "s3:GetObject",\n          "Effect": "Allow",\n          "Resource": [\n              "arn:aws:s3:::abc",\n              "arn:aws:s3:::abc/*"\n          ],\n      }\n  ]\n}',
    )
    include_accounts: Optional[List[str]] = Field(
        None,
        description="An array of accounts to include this policy on. This is only relevant for templated\nIAM roles. By default, the change will apply to all of the accounts the template is deployed to.",
        example=["account_a", "account_b", "..."],
    )
    exclude_accounts: Optional[List[str]] = Field(
        None,
        description="An array of accounts to explicitly exclude this policy on. This is only relevant for templated\nIAM roles. By default, exclude_accounts is null and the change will apply to all of the accounts",
        example=["account_a", "account_b", "..."],
    )
    extra_actions: Optional[List[str]] = Field(
        None,
        description="An array with a list of extra actions the user wants appended to the policy",
        example=["*", "s3:getobject", "s3:list*"],
    )


class AdvancedChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex=r"advanced")
    iam_action: Optional[str] = Field(None, example="kinesis:AddTagsToStream")
    resource: Optional[str] = Field(None, example="*")


class GenericChangeGeneratorModel(ChangeGeneratorModel):
    action_groups: List[str]
    resource_arn: Union[str, List[str]] = Field(
        ...,
        description="The ARN(s) of the resource being accessed. This is often SQS/SNS/S3/etc. ARNs. It is possible that the\nresource policies will need to be modified if the change is approved and successful.",
        example=["arn:aws:sqs:us-east-1:123456789012:sqs_queue"],
    )


class CrudChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex=r"crud_lookup")
    action_groups: List[str]
    service_name: str


class S3ChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex=r"s3")
    resource_arn: Union[str, List[str]] = Field(
        ...,
        description="The ARN(s) of the S3 resource(s) being accessed.",
        example=["arn:aws:s3:::example_bucket"],
    )
    bucket_prefix: str = Field(..., example="/awesome/prefix/*")
    action_groups: List[str]


class CustomIamChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex=r"custom_iam")
    policy: Dict[str, Any]


class SQSChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex=r"sqs")
    action_groups: List[str]


class SNSChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex=r"sns")
    action_groups: List[str]


class SESChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex=r"ses")
    from_address: str
    action_groups: Optional[List[str]] = None


class InlinePolicyChangeModel(ChangeModel):
    policy_name: Optional[str] = None
    new: Optional[bool] = True
    action: Optional[Action] = None
    change_type: Optional[constr(regex=r"inline_policy")] = None
    policy: Optional[PolicyModel] = None
    old_policy: Optional[PolicyModel] = None


class AssumeRolePolicyChangeModel(ChangeModel):
    change_type: Optional[constr(regex=r"assume_role_policy")] = None
    policy: Optional[PolicyModel] = None
    old_policy: Optional[PolicyModel] = None
    source_change_id: Optional[str] = Field(
        None,
        description="the change model ID of the source change, that this change was generated from",
    )


class ResourcePolicyChangeModel(ChangeModel):
    change_type: Optional[constr(regex=r"resource_policy|sts_resource_policy")] = None
    arn: constr(
        regex=r"(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    )
    source_change_id: Optional[str] = Field(
        None,
        description="the change model ID of the source change, that this change was generated from",
    )
    supported: Optional[bool] = Field(
        None,
        description="whether we currently support this type of resource policy change or not",
    )
    policy: PolicyModel
    old_policy: Optional[PolicyModel] = None


class ManagedPolicyResourceChangeModel(ChangeModel):
    new: Optional[bool] = True
    change_type: Optional[constr(regex=r"managed_policy_resource")] = None
    policy: Optional[PolicyModel] = None
    old_policy: Optional[PolicyModel] = None


class ChangeModelArray(BaseModel):
    changes: List[
        Union[
            InlinePolicyChangeModel,
            ManagedPolicyChangeModel,
            PermissionsBoundaryChangeModel,
            ResourcePolicyChangeModel,
            AssumeRolePolicyChangeModel,
            ResourceTagChangeModel,
            GenericFileChangeModel,
            ManagedPolicyResourceChangeModel,
        ]
    ]


class CloudAccountModelArray(BaseModel):
    accounts: Optional[List[CloudAccountModel]] = None


class CommentModel(BaseModel):
    id: str
    timestamp: datetime
    edited: Optional[bool] = None
    last_modified: Optional[datetime] = None
    user_email: str
    user: Optional[UserModel] = None
    text: str


class RequestCreationModel(BaseModel):
    changes: ChangeModelArray
    justification: Optional[str] = None
    dry_run: Optional[bool] = False
    admin_auto_approve: Optional[bool] = False
    expiration_date: Optional[int] = Field(
        None,
        description="Date to expire requested policy, in the format of YYYYmmdd",
        example=20210905,
    )


class ExtendedRequestModel(RequestModel):
    changes: ChangeModelArray
    requester_info: UserModel
    reviewer: Optional[str] = None
    comments: Optional[List[CommentModel]] = None
    expiration_date: Optional[int] = Field(
        None,
        description="Date to expire requested policy, in the format of YYYYmmdd",
        example=20210905,
    )


class ChangeGeneratorModelArray(BaseModel):
    changes: List[
        Union[
            S3ChangeGeneratorModel,
            SQSChangeGeneratorModel,
            SNSChangeGeneratorModel,
            SESChangeGeneratorModel,
            CrudChangeGeneratorModel,
            GenericChangeGeneratorModel,
            CustomIamChangeGeneratorModel,
        ]
    ]


class RequestCreationResponse(BaseModel):
    errors: Optional[int] = None
    request_created: Optional[bool] = None
    request_id: Optional[str] = None
    request_url: Optional[str] = None
    action_results: Optional[List[ActionResult]] = None
    extended_request: Optional[ExtendedRequestModel] = None
