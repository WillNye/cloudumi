import ssl
import sys

import bleach
import requests as requests_sync
import tenacity
import ujson as json
from botocore.exceptions import ClientError
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat

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
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import send_communications_policy_change_request_v2

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()

log = config.get_logger(__name__)


class Aws:
    """The AWS class handles interactions with AWS."""

    async def call_user_lambda(
        self, role: str, user_email: str, account_id: str, user_role_name: str = "user"
    ) -> str:
        """Call out to the lambda function to provision the per-user role for the account."""
        raise NotImplementedError("This feature isn't enabled in ConsoleMe OSS")

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
        host: str,
        enforce_ip_restrictions: bool = True,
        user_role: bool = False,
        account_id: str = None,
        custom_ip_restrictions: list = None,
        read_only: bool = False,
        session_policies: list[str] = None,
    ) -> dict:
        """Get Credentials will return the list of temporary credentials from AWS."""
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": user,
            "role": role,
            "host": host,
            "enforce_ip_restrictions": enforce_ip_restrictions,
            "custom_ip_restrictions": custom_ip_restrictions,
            "message": "Generating credentials",
        }
        client = boto3_cached_conn(
            "sts",
            host,
            user,
            region=config.region,
            sts_client_kwargs=dict(
                region_name=config.region,
                endpoint_url=f"https://sts.{config.region}.amazonaws.com",
            ),
            client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
            session_name=sanitize_session_name("noq_get_credentials"),
        )

        assume_role_kwargs = dict(
            RoleArn=role,
            RoleSessionName=user.lower(),
            DurationSeconds=config.get_host_specific_key(
                "aws.session_duration", host, 3600
            ),
        )

        session_policies = session_policies or set()
        if read_only:
            session_policies.update(
                config.get_host_specific_key(
                    "aws.policies.read_only_policies",
                    host,
                    ["arn:aws:iam::aws:policy/ReadOnlyAccess"],
                )
            )
        if session_policies:
            assume_role_kwargs["PolicyArns"] = [
                {"arn": policy_arn} for policy_arn in session_policies
            ]
        ip_restrictions = config.get_host_specific_key("aws.ip_restrictions", host)
        stats.count(
            "aws.get_credentials",
            tags={
                "role": role,
                "user": user,
                "host": host,
            },
        )

        # If this is a dynamic request, then we need to fetch the role details, call out to the lambda
        # wait for it to complete, assume the role, and then return the assumed credentials back.
        if user_role:
            stats.count(
                "aws.call_user_lambda",
                tags={
                    "role": role,
                    "user": user,
                    "host": host,
                },
            )
            try:
                role = await self.call_user_lambda(role, user, account_id)
            except Exception as e:
                raise e

        await raise_if_background_check_required_and_no_background_check(
            role, user, host
        )

        # Set transitive tags to identify user
        transitive_tag_keys = []
        tags = []
        transitive_tag_enabled = config.get_host_specific_key(
            "aws.transitive_session_tags.enabled", host
        )
        if transitive_tag_enabled:
            role_transitive_tag_key_identifying_user = config.get_host_specific_key(
                "aws.transitive_session_tags.user_key",
                host,
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
            if enforce_ip_restrictions and ip_restrictions:
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
                                    NotIpAddress={"aws:SourceIP": ip_restrictions},
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
            elif custom_ip_restrictions:
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
                                        "aws:SourceIP": custom_ip_restrictions
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
                and config.get_host_specific_key(
                    "aws.automatically_update_role_trust_policies", host
                )
            ):
                await update_assume_role_policy_trust_noq(
                    host, user, role.split("/")[-1], role.split(":")[4]
                )
                raise RoleTrustPolicyModified(
                    "Role trust policy was modified. Please try again in a few seconds."
                )
            raise

    async def generate_url(
        self,
        user: str,
        role: str,
        host: str,
        region: str = "us-east-1",
        user_role: bool = False,
        account_id: str = None,
        read_only: bool = False,
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
        ip_restrictions_enabled = config.get_host_specific_key(
            "policies.ip_restrictions", host, False
        )
        credentials = await self.get_credentials(
            user,
            role,
            host,
            user_role=user_role,
            account_id=account_id,
            enforce_ip_restrictions=ip_restrictions_enabled,
            read_only=read_only,
        )

        credentials_d = {
            "sessionId": credentials.get("Credentials", {}).get("AccessKeyId"),
            "sessionKey": credentials.get("Credentials", {}).get("SecretAccessKey"),
            "sessionToken": credentials.get("Credentials", {}).get("SessionToken"),
        }

        req_params = {
            "Action": "getSigninToken",
            "Session": bleach.clean(json.dumps(credentials_d)),
            "DurationSeconds": config.get_host_specific_key(
                "aws.session_duration", host, 3600
            ),
        }

        http_client = AsyncHTTPClient(force_instance=True)

        url_with_params: str = url_concat(
            config.get_host_specific_key(
                "aws.federation_url",
                host,
                "https://signin.aws.amazon.com/federation",
            ),
            req_params,
        )
        r = await http_client.fetch(url_with_params, ssl_options=ssl.SSLContext())
        token = json.loads(r.body)

        login_req_params = {
            "Action": "login",
            "Issuer": config.get_host_specific_key("aws.issuer", host),
            "Destination": (
                "{}".format(
                    config.get_host_specific_key(
                        "aws.console_url",
                        host,
                        "https://{}.console.aws.amazon.com",
                    ).format(region)
                )
            ),
            "SigninToken": bleach.clean(token.get("SigninToken")),
            "SessionDuration": config.get_host_specific_key(
                "aws.session_duration", host, 3600
            ),
        }

        r2 = requests_sync.Request(
            "GET",
            config.get_host_specific_key(
                "aws.federation_url",
                host,
                "https://signin.aws.amazon.com/federation",
            ),
            params=login_req_params,
        )
        url = r2.prepare().url
        return url

    async def send_communications_new_policy_request(
        self, extended_request, admin_approved, approval_probe_approved, host
    ):
        """
        Optionally send a notification when there's a new policy change request

        :param approval_probe_approved:
        :param admin_approved:
        :param extended_request:
        :return:
        """
        await send_communications_policy_change_request_v2(extended_request, host)
        return

    @staticmethod
    def handle_detected_role(role):
        pass

    async def should_auto_approve_policy_v2(
        self, extended_request, user, user_groups, host
    ):
        return {"approved": False}


def init():
    """Initialize the AWS plugin."""
    return Aws()
