import os
import ssl
import sys

import bleach
import requests as requests_sync
import sentry_sdk
import tenacity
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError
from policy_sentry.util.arns import parse_arn
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat

import common.lib.noq_json as json
from common.aws.iam.role.models import IAMRole
from common.aws.iam.role.utils import update_assume_role_policy_trust_noq
from common.config import config
from common.exceptions.exceptions import (
    RoleTrustPolicyModified,
    UserRoleNotAssumableYet,
)
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.aws.utils import (
    raise_if_background_check_required_and_no_background_check,
)
from common.lib.generic import get_principal_friendly_name
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import send_communications_policy_change_request_v2
from common.models import Action, ExtendedRequestModel

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()

log = config.get_logger(__name__)


class Aws:
    """The AWS class handles interactions with AWS."""

    async def call_user_lambda(
        self, role: str, user_email: str, account_id: str, user_role_name: str = "user"
    ) -> str:
        """Call out to the lambda function to provision the per-user role for the account."""
        raise NotImplementedError("This feature isn't enabled in NOQ OSS")

    @tenacity.retry(
        wait=tenacity.wait_fixed(2),
        stop=tenacity.stop_after_attempt(10),
        retry=(
            tenacity.retry_if_exception_type(UserRoleNotAssumableYet)
            | tenacity.retry_if_exception_type(RoleTrustPolicyModified)
        ),
    )
    async def get_credentials(
        self,
        user: str,
        role: str,
        tenant: str,
        enforce_ip_restrictions: bool = True,
        user_role: bool = False,
        account_id: str = None,
        custom_ip_restrictions: list = None,
        read_only: bool = False,
        session_policies: list[str] = None,
        requester_ip: str = None,
    ) -> dict:
        """Get Credentials will return the list of temporary credentials from AWS."""
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": user,
            "role": role,
            "tenant": tenant,
            "enforce_ip_restrictions": enforce_ip_restrictions,
            "custom_ip_restrictions": custom_ip_restrictions,
            "message": "Generating credentials",
        }
        client = boto3_cached_conn(
            "sts",
            tenant,
            user,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_tenant_specific_key(
                "boto3.client_kwargs", tenant, {}
            ),
            session_name=sanitize_session_name("noq_get_credentials"),
        )

        assume_role_kwargs = dict(
            RoleArn=role,
            RoleSessionName=user.lower(),
            DurationSeconds=config.get_tenant_specific_key(
                "aws.session_duration", tenant, 3600
            ),
        )

        session_policies = session_policies or set()
        if read_only:
            session_policies.update(
                config.get_tenant_specific_key(
                    "aws.policies.read_only_policies",
                    tenant,
                    ["arn:aws:iam::aws:policy/ReadOnlyAccess"],
                )
            )
        if session_policies:
            assume_role_kwargs["PolicyArns"] = [
                {"arn": policy_arn} for policy_arn in session_policies
            ]
        ip_restrictions = config.get_tenant_specific_key("aws.ip_restrictions", tenant)
        stats.count(
            "aws.get_credentials",
            tags={
                "role": role,
                "user": user,
                "tenant": tenant,
            },
        )

        # We are adding requester ip address to both ip_restrictions and custom_ip_restrictions
        # AWS wants CIDR notation, so when we inject the request IP address, we have to turn it into a
        # CIDR notation. https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing
        extended_ip_restrictions = []
        extended_custom_ip_restrictions = []
        is_requester_ip_restriction_enabled = config.get_tenant_specific_key(
            "policies.ip_restrictions_on_requesters_ip", tenant, False
        )
        if is_requester_ip_restriction_enabled:
            # Detecting loop-back address is really on for local dev
            # Therefore, we check against the existence of the AWS_PROFILE environment
            # variable which is really only set in local dev.
            # In the event of loop-back address, we have to check what's remote IP is being
            # seen by AWS endpoint.
            if (requester_ip == "::1" or "127.0.0.1") and os.getenv(
                "AWS_PROFILE", None
            ) == "NoqSaasRoleLocalDev":
                try:
                    requester_ip = requests_sync.get(
                        "https://checkip.amazonaws.com"
                    ).text.strip()
                except Exception as e:
                    requester_ip = None
                    log.debug({**log_data, "exception": "{0}".format(e)})
            if not requester_ip:
                raise Exception("Not able to satisfy requester ip restriction")
            if ":" in requester_ip:
                # IPv6 - Debate whether /64 is the fine enough restriction
                # /64 IPv6 subnet is IETF standard size and at least reachable
                # to a network customer.
                extended_ip_restrictions.append(f"{requester_ip}/64")
                extended_custom_ip_restrictions.append(f"{requester_ip}/64")
            elif "." in requester_ip:
                # IPv4
                extended_ip_restrictions.append(f"{requester_ip}/32")
                extended_custom_ip_restrictions.append(f"{requester_ip}/32")
        if ip_restrictions:
            extended_ip_restrictions.extend(ip_restrictions)
        if custom_ip_restrictions:
            extended_custom_ip_restrictions.extend(custom_ip_restrictions)

        # If this is a dynamic request, then we need to fetch the role details, call out to the lambda
        # wait for it to complete, assume the role, and then return the assumed credentials back.
        if user_role:
            stats.count(
                "aws.call_user_lambda",
                tags={
                    "role": role,
                    "user": user,
                    "tenant": tenant,
                },
            )
            try:
                role = await self.call_user_lambda(role, user, account_id)
            except Exception as e:
                raise e

        await raise_if_background_check_required_and_no_background_check(
            role, user, tenant
        )

        # Set transitive tags to identify user
        transitive_tag_keys = []
        tags = []
        transitive_tag_enabled = config.get_tenant_specific_key(
            "aws.transitive_session_tags.enabled", tenant
        )
        if transitive_tag_enabled:
            role_transitive_tag_key_identifying_user = config.get_tenant_specific_key(
                "aws.transitive_session_tags.user_key",
                tenant,
                "noq_transitive_session_tag_user",
            )

            if role_transitive_tag_key_identifying_user:
                tags = [
                    {
                        "Key": role_transitive_tag_key_identifying_user,
                        "Value": user,
                    }
                ]
                transitive_tag_keys = [role_transitive_tag_key_identifying_user]
                assume_role_kwargs["Tags"] = tags
                assume_role_kwargs["TransitiveTagKeys"] = transitive_tag_keys

        try:
            if enforce_ip_restrictions and extended_ip_restrictions:
                # Used to further restrict user permissions
                # https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html
                assume_role_kwargs["Policy"] = json.dumps(
                    dict(
                        Version="2012-10-17",
                        Statement=[
                            dict(
                                Effect="Deny",
                                Action="*",
                                Resource="*",
                                Condition=dict(
                                    NotIpAddress={
                                        "aws:SourceIP": extended_ip_restrictions
                                    },
                                    Null={
                                        "aws:Via": "true",
                                        "aws:PrincipalTag/AWSServiceTrust": "true",
                                    },
                                    StringNotLike={
                                        "aws:PrincipalArn": [
                                            "arn:aws:iam::*:role/aws:*"
                                        ]
                                    },
                                ),
                            ),
                            dict(Effect="Allow", Action="*", Resource="*"),
                        ],
                    )
                )
            elif extended_custom_ip_restrictions:
                assume_role_kwargs["Policy"] = json.dumps(
                    dict(
                        Version="2012-10-17",
                        Statement=[
                            dict(
                                Effect="Deny",
                                Action="*",
                                Resource="*",
                                Condition=dict(
                                    NotIpAddress={
                                        "aws:SourceIP": extended_custom_ip_restrictions
                                    },
                                    Null={
                                        "aws:Via": "true",
                                        "aws:PrincipalTag/AWSServiceTrust": "true",
                                    },
                                    StringNotLike={
                                        "aws:PrincipalArn": [
                                            "arn:aws:iam::*:role/aws:*"
                                        ]
                                    },
                                ),
                            ),
                            dict(Effect="Allow", Action="*", Resource="*"),
                        ],
                    )
                )

            credentials = await aio_wrapper(
                client.assume_role,
                **assume_role_kwargs,
            )
            credentials["Credentials"]["Expiration"] = int(
                credentials["Credentials"]["Expiration"].timestamp()
            )
            log.debug(
                {**log_data, "access_key_id": credentials["Credentials"]["AccessKeyId"]}
            )
            return credentials
        except ClientError as e:
            # TODO(ccastrapel): Determine if user role was really just created, or if this is an older role.
            if user_role:
                raise UserRoleNotAssumableYet(e.response["Error"])
            if (
                e.response["Error"]["Code"] == "AccessDenied"
                and "is not authorized to perform: sts:AssumeRole on resource: "
                in e.response["Error"]["Message"]
                and config.get_tenant_specific_key(
                    "aws.automatically_update_role_trust_policies", tenant
                )
            ):
                await update_assume_role_policy_trust_noq(
                    tenant, user, role.split("/")[-1], role.split(":")[4]
                )
                raise RoleTrustPolicyModified(
                    "Role trust policy was modified. Please try again in a few seconds."
                )
            raise

    async def generate_url(
        self,
        user: str,
        role: str,
        tenant: str,
        region: str = "us-east-1",
        user_role: bool = False,
        account_id: str = None,
        read_only: bool = False,
        requester_ip: str = None,
    ) -> str:
        """Generate URL will get temporary credentials and craft a URL with those credentials."""
        function = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "user": user,
            "role": role,
            "message": "Generating authenticated AWS console URL",
        }
        log.debug(log_data)
        ip_restrictions_enabled = config.get_tenant_specific_key(
            "policies.ip_restrictions", tenant, False
        )
        credentials = await self.get_credentials(
            user,
            role,
            tenant,
            user_role=user_role,
            account_id=account_id,
            enforce_ip_restrictions=ip_restrictions_enabled,
            read_only=read_only,
            requester_ip=requester_ip,
        )

        credentials_d = {
            "sessionId": credentials.get("Credentials", {}).get("AccessKeyId"),
            "sessionKey": credentials.get("Credentials", {}).get("SecretAccessKey"),
            "sessionToken": credentials.get("Credentials", {}).get("SessionToken"),
        }

        req_params = {
            "Action": "getSigninToken",
            "Session": bleach.clean(json.dumps(credentials_d)),
            "DurationSeconds": config.get_tenant_specific_key(
                "aws.session_duration", tenant, 3600
            ),
        }

        http_client = AsyncHTTPClient(force_instance=True)

        url_with_params: str = url_concat(
            config.get_tenant_specific_key(
                "aws.federation_url",
                tenant,
                "https://signin.aws.amazon.com/federation",
            ),
            req_params,
        )
        r = await http_client.fetch(url_with_params, ssl_options=ssl.SSLContext())
        token = json.loads(r.body)

        login_req_params = {
            "Action": "login",
            "Issuer": config.get_tenant_specific_key("aws.issuer", tenant),
            "Destination": (
                "{}".format(
                    config.get_tenant_specific_key(
                        "aws.console_url",
                        tenant,
                        "https://{}.console.aws.amazon.com",
                    ).format(region)
                )
            ),
            "SigninToken": bleach.clean(token.get("SigninToken")),
            "SessionDuration": config.get_tenant_specific_key(
                "aws.session_duration", tenant, 3600
            ),
        }

        r2 = requests_sync.Request(
            "GET",
            config.get_tenant_specific_key(
                "aws.federation_url",
                tenant,
                "https://signin.aws.amazon.com/federation",
            ),
            params=login_req_params,
        )
        url = r2.prepare().url
        return url

    async def send_communications_new_policy_request(
        self, extended_request, admin_approved, approval_rule_approved, tenant
    ):
        """
        Optionally send a notification when there's a new policy change request

        :param approval_rule_approved:
        :param admin_approved:
        :param extended_request:
        :return:
        """
        await send_communications_policy_change_request_v2(extended_request, tenant)
        return

    @staticmethod
    def handle_detected_role(role):
        pass

    async def should_auto_approve_policy_v2(
        self, extended_request: ExtendedRequestModel, user, user_groups, tenant
    ):
        """
                This will auto-approve a policy based on a comparison of policy to auto-approval rules with AWS Zelkova.
                Zelkova is not GA at the time of writing, hence this code is not in OSS NOQ. Anyone wishing to make use of
                this code will need to perform the following steps:

                1) You'll need to ask your AWS TAM to enable Zelkova on the account you have NOQ deployed to.
                2) You'll need to put a special JSON model for Zelkova in your NOQ instances under
                /etc/aws/models/zelkova/2018-01-29/service-2.json . If you run NOQ locally for development, also put it
                in ~/.aws/models/zelkova/2018-01-29/service-2.json
                3) You'll need to make your own internal NOQ plugin set if you don't already have one.
                Basically, copy the contents of the default_plugins folder to a new repository internal to your company.
                You'll need to pip install this into NOQ OSS for your deployment.
                4) In your plugin set, there's a function called should_auto_approve_policy_v2 that needs to be overridden.
                We can provide the code to this when ready.

                Once this is set up, you can use NOQ's Dynamic Configuration (ex: https://your_NOQ_domain/config)
                and write rules. Here's an example:

        policy_request_autoapprove_rules:
          enabled: true
          rules:
            - name: common_s3
              description: Automatically approve requests to common, shared S3 buckets
              policy: |-
                {
                  "Statement": [
                    {
                      "Action": [
                        "s3:ListBucket",
                        "s3:ListBucketVersions",
                        "s3:GetObject",
                        "s3:GetObjectTagging",
                        "s3:GetObjectVersion",
                        "s3:GetObjectVersionTagging",
                        "s3:GetObjectAcl",
                        "s3:GetObjectVersionAcl",
                        "s3:PutObject",
                        "s3:PutObjectTagging",
                        "s3:PutObjectVersionTagging",
                        "s3:ListMultipartUploadParts*",
                        "s3:AbortMultipartUpload",
                        "s3:DeleteObject",
                        "s3:DeleteObjectTagging",
                        "s3:DeleteObjectVersion",
                        "s3:DeleteObjectVersionTagging",
                        "s3:RestoreObject"
                      ],
                      "Effect": "Allow",
                      "Resource": [
                        "arn:aws:s3:::*.example.s3.shared.bucket",
                        "arn:aws:s3:::*.example.s3.shared.bucket/*",
                        "arn:aws:s3:::*.example.s3.shared.bucket2",
                        "arn:aws:s3:::*.example.s3.shared.bucket2/*"
                      ]
                    }
                  ]
                }
            - name: ses_rule
              description: Automatically approve SES requests scoped to a specific e-mail suffix
              policy: |-
                {
                  "Statement": [
                    {
                         "Action": [
                             "ses:SendEmail",
                              "ses:SendRawEmail"],
                         "Condition": {
                            "StringLike": {
                            "ses:FromAddress": "*@mail.example.com"
                            }
                          },
                         "Effect": "Allow",
                         "Resource": "arn:aws:ses:*:123456789012:identity/mail.example.com"
                   }
                  ]
                }
            - name: cde_s3
              description: 'Automatically approve S3 team read/write requests'
              required_user_or_group:
                - 's3team@example.com'
              policy: |-
                {
                  "Statement": [
                    {
                      "Action": [
                        "s3:ListBucket",
                        "s3:ListBucketVersions",
                        "s3:GetObject",
                        "s3:GetObjectTagging",
                        "s3:GetObjectVersion",
                        "s3:GetObjectVersionTagging",
                        "s3:GetObjectAcl",
                        "s3:GetObjectVersionAcl",
                        "s3:PutObject",
                        "s3:PutObjectTagging",
                        "s3:PutObjectVersionTagging",
                        "s3:ListMultipartUploadParts*",
                        "s3:AbortMultipartUpload",
                        "s3:DeleteObject",
                        "s3:DeleteObjectTagging",
                        "s3:DeleteObjectVersion",
                        "s3:DeleteObjectVersionTagging"
                      ],
                      "Effect": "Allow",
                      "Resource": [
                        "arn:aws:s3:::*"
                      ]
                    }
                  ]
                }
            - name: dbteam_rds
              description: 'Automatically approve DB team RDS requests'
              required_user_or_group:
                - 'db_team@example.com'
              policy: |-
                {
                  "Statement": [
                    {
                      "Action": [
                        "rds:*"
                      ],
                      "Effect": "Allow",
                      "Resource": [
                        "*"
                      ]
                    }
                  ]
                }
            - name: networking_eni_autoattach
              description: 'Automatically approve networking team ENI AutoAttach requests'
              required_user_or_group:
                - 'networking_team@example.com'
              policy: |-
                {
                    "Statement": [
                        {
                            "Action": [
                                "ec2:AttachNetworkInterface",
                                "ec2:Describe*",
                                "ec2:DetachNetworkInterface"
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "*"
                            ]
                        }
                    ],
                    "Version": "2012-10-17"
                }
            - name: same_account_sqs
              description: Automatically approve same-account SQS requests
              policy: |-
                {
                  "Statement": [
                    {
                      "Action": [
                        "sqs:GetQueueAttributes",
                        "sqs:GetQueueUrl",
                        "sqs:SendMessage",
                        "sqs:ReceiveMessage",
                        "sqs:DeleteMessage",
                        "sqs:SetQueueAttributes",
                        "sqs:PurgeQueue"
                      ],
                      "Effect": "Allow",
                      "Resource": [
                        "arn:aws:sqs:*:{account_id}:*"
                      ]
                    }
                  ]
                }
            - name: same_account_sns
              description: Automatically approve same-account SNS requests
              policy: |-
                {
                  "Statement": [
                    {
                      "Action": [
                        "sns:GetEndpointAttributes",
                        "sns:GetTopicAttributes",
                        "sns:Publish",
                        "sns:Subscribe",
                        "sns:ConfirmSubscription",
                        "sns:Unsubscribe"
                      ],
                      "Effect": "Allow",
                      "Resource": [
                        "arn:aws:sns:*:{account_id}:*"
                      ]
                    }
                  ]
                }
            - name: ec2:AssignIpv6Addresses
              description: Automatically approve ec2 AssignIpv6Addresses requests
              policy: |-
                {
                    "Statement":[
                        {
                            "Action":[
                                "ec2:AssignIpv6Addresses"
                            ],
                            "Effect":"Allow",
                            "Resource":[
                                "*"
                            ]
                        }
                    ]
                }
            - name: common_app_permissions
              description: Automatically approve requests to common application permissions
              accounts:
                blocklist:
                  - "123456789012" # the account ID to our really sensitive PCI account
              policy: |-
                {
                  "Version": "2012-10-17",
                  "Statement": [
                    {
                      "Sid": "prana",
                      "Effect": "Allow",
                      "Action": [
                        "route53:listresourcerecordsets",
                        "route53:changeresourcerecordsets",
                        "route53:gethostedzone",
                        "route53:listhostedzones"
                      ],
                      "Resource": [
                        "arn:aws:route53:::hostedzone/BLAH"
                      ]
                    }
                  ]
                }
        """
        principal = await get_principal_friendly_name(extended_request.principal)
        log_data: dict = {
            "function": f"{__name__}.{sys._getframe().f_code.co_name}",
            "user": user,
            "principal": principal,
            "request": extended_request.dict(),
            "message": "Determining if request should be auto-approved",
        }
        log.debug(log_data)

        try:
            if not config.get_tenant_specific_key(
                "policy_request_autoapprove_rules.enabled", tenant
            ):
                log_data["message"] = "Auto-approval rules are disabled"
                log_data["approved"] = False
                log.debug(log_data)
                return {"approved": False}

            # AwsResource types are the only resource types currently supported for auto-approval.
            if extended_request.principal.principal_type != "AwsResource":
                return {"approved": False}
            principal_arn = extended_request.principal.principal_arn
            arn_parsed = parse_arn(principal_arn)
            iam_role = await IAMRole.get(tenant, arn_parsed["account"], principal_arn)

            if iam_role.templated:
                log_data["message"] = "Auto-approval not available for templated roles"
                log_data["approved"] = False
                log.debug(log_data)
                return {"approved": False}

            try:
                zelkova = boto3_cached_conn(
                    "zelkova",
                    "_global_.accounts.zelkova",
                    user,
                    service_type="client",
                    future_expiration_minutes=60,
                )
            except Exception as e:  # noqa
                zelkova = None
                sentry_sdk.capture_exception()

            approving_rules = []

            # Currently the only allowances are: Inline policies
            for change in extended_request.changes.changes:
                # Exclude auto-generated resource policies from check as we don't apply these
                if change.change_type == "resource_policy" and change.autogenerated:
                    continue
                # We currently only support for attaching inline policies, and only if zelkova
                if (
                    change.change_type != "inline_policy"
                    or change.action != Action.attach
                    or not zelkova
                ):
                    log_data[
                        "message"
                    ] = "Successfully finished running auto-approval rules"
                    log_data["approved"] = False
                    log.info(log_data)
                    return {"approved": False}

                rules_result = False
                account_id = principal_arn.split(":")[4]

                for rule in config.get_tenant_specific_key(
                    "policy_request_autoapprove_rules.rules", tenant, []
                ):
                    log_data["rule"] = rule["name"]
                    log_data["requested_policy"] = change.policy.json()
                    log_data["message"] = "Running rule on requested policy"
                    log.debug(log_data)
                    rule_result = False
                    policy_document = change.policy.policy_document

                    # Do not approve "Deny" policies automatically
                    statements = policy_document.get("Statement", [])
                    for statement in statements:
                        if statement.get("Effect") == "Deny":
                            log_data[
                                "message"
                            ] = "Successfully finished running auto-approval rules"
                            log_data["approved"] = False
                            log.debug(log_data)
                            return {"approved": False}

                    requested_policy_text = json.dumps(policy_document)
                    zelkova_result = await sync_to_async(zelkova.compare_policies)(
                        Items=[
                            {
                                "Policy0": requested_policy_text,
                                "Policy1": rule["policy"].replace(
                                    "{account_id}", account_id
                                ),
                                "ResourceType": "IAM",
                            }
                        ]
                    )

                    comparison = zelkova_result["Items"][0]["Comparison"]

                    allow_listed = False
                    allowed_group = False

                    # Rule will fail if ARN account ID is not in the rule's account allow-list. Default allow-list is
                    # *
                    for account in rule.get("accounts", {}).get("allowlist", ["*"]):
                        if account == "*" or account_id == str(account):
                            allow_listed = True
                            break

                    if not allow_listed:
                        comparison = "DENIED_BY_ALLOWLIST"

                    # Rule will fail if ARN account ID is in the rule's account blocklist
                    for account in rule.get("accounts", {}).get("blocklist", []):
                        if account_id == str(account):
                            comparison = "DENIED_BY_BLOCKLIST"

                    for group in rule.get("required_user_or_group", ["*"]):
                        for g in user_groups:
                            if group == "*" or group == g or group == user:
                                allowed_group = True
                                break

                    if not allowed_group:
                        comparison = "DENIED_BY_ALLOWEDGROUPS"

                    if comparison in ["LESS_PERMISSIVE", "EQUIVALENT"]:
                        rule_result = True
                        rules_result = True
                        approving_rules.append(
                            {"name": rule["name"], "policy": change.policy_name}
                        )
                        log_data["comparison"] = comparison
                        log_data["rule_result"] = rule_result
                        log.debug(log_data)
                        # Already have an approving rule, break out of for loop
                        break
                    log_data["comparison"] = comparison
                    log_data["rule_result"] = rule_result
                    log.debug(log_data)
                if not rules_result:
                    # If one of the policies in the request fails to auto-approve, everything fails
                    log_data[
                        "message"
                    ] = "Successfully finished running auto-approval rules"
                    log_data["approved"] = False
                    log.debug(log_data)
                    stats.count(
                        f"{log_data['function']}.auto_approved",
                        tags={"arn": principal_arn, "result": False},
                    )
                    return {"approved": False}

            # All changes have been checked, and none of them returned false
            log_data["message"] = "Successfully finished running auto-approval rules"
            log_data["approved"] = True
            log.debug(log_data)
            stats.count(
                f"{log_data['function']}.auto_approved",
                tags={"arn": principal_arn, "result": True},
            )
            return {"approved": True, "approving_rules": approving_rules}
        except Exception as e:
            sentry_sdk.capture_exception()
            log_data["error"] = str(e)
            log_data["message"] = "Exception occurred while checking auto-approval rule"
            log.error(log_data, exc_info=True)
            return {"approved": False}


def init():
    """Initialize the AWS plugin."""
    return Aws()
