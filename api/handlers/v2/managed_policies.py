import sentry_sdk
import tornado.escape
import ujson as json

from common.aws.iam.role.utils import get_role_managed_policy_documents
from common.config import config
from common.config.models import ModelAdapter
from common.exceptions.exceptions import MustBeFte
from common.handlers.base import BaseAPIV2Handler
from common.lib.asyncio import aio_wrapper
from common.lib.aws.iam import (
    get_all_iam_managed_policies_for_account,
    get_managed_policy_document,
    get_user_managed_policy_documents,
)
from common.models import SpokeAccount, Status2, WebResponse

log = config.get_logger()


class ManagedPoliciesOnPrincipalHandler(BaseAPIV2Handler):
    """
    Handler for /api/v2/managed_policies_on_principal/{arn}

    Returns managed policy and latest policy version information for a principal
    """

    async def get(self, arn):
        host = self.ctx.host
        if (
            config.get_host_specific_key(
                "policy_editor.disallow_contractors", host, True
            )
            and self.contractor
        ):
            if self.user not in config.get(
                "groups.can_bypass_contractor_restrictions", []
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        errors = []
        if not arn.startswith("arn:aws:iam::"):
            errors.append("ARN must start with 'arn:aws:iam::'")

        principal_name = tornado.escape.xhtml_escape(arn.split("/")[-1])
        try:
            principal_type = tornado.escape.xhtml_escape(
                arn.split(":")[5].split("/")[0]
            )
        except Exception:
            principal_type = None
        try:
            account_id = tornado.escape.xhtml_escape(arn.split(":")[4])
        except Exception:
            account_id = None

        if principal_type not in ["role", "user"]:
            errors.append(f"Principal type must be role or user. not {principal_type}")

        log_data = {
            "function": "ManagedPoliciesOnRoleHandler.get",
            "user": self.user,
            "ip": self.ip,
            "message": "Retrieving managed policies for role",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "principal_name": principal_name,
            "principal_type": principal_type,
            "host": host,
        }

        log.debug(log_data)
        if errors:
            log.error(
                {**log_data, "errors": errors, "message": "Unable to process request"}
            )
            res = WebResponse(
                status=Status2.error,
                reason="bad_request",
                status_code=400,
                errors=errors,
            )
            self.write(res.json())
            return

        if principal_type == "role":
            managed_policy_details = await aio_wrapper(
                get_role_managed_policy_documents,
                {"RoleName": principal_name},
                account_number=account_id,
                assume_role=ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", host)
                .with_query({"account_id": account_id})
                .first.name,
                region=config.region,
                retry_max_attempts=2,
                client_kwargs=config.get_host_specific_key(
                    "boto3.client_kwargs", host, {}
                ),
                host=host,
            )
        elif principal_type == "user":
            managed_policy_details = await aio_wrapper(
                get_user_managed_policy_documents,
                {"UserName": principal_name},
                account_number=account_id,
                assume_role=ModelAdapter(SpokeAccount)
                .load_config("spoke_accounts", host)
                .with_query({"account_id": account_id})
                .first.name,
                region=config.region,
                retry_max_attempts=2,
                client_kwargs=config.get_host_specific_key(
                    "boto3.client_kwargs", host, {}
                ),
                host=host,
            )
        else:
            raise Exception("Invalid principal type")
        res = WebResponse(
            status=Status2.success,
            status_code=200,
            data=managed_policy_details,
        )
        self.write(res.json())


class ManagedPoliciesHandler(BaseAPIV2Handler):
    """
    Handler for /api/v2/managed_policies/{policyArn}

    Returns details about the specified managed policy
    """

    async def get(self, policy_arn: str):
        host = self.ctx.host
        if (
            config.get_host_specific_key(
                "policy_editor.disallow_contractors", host, True
            )
            and self.contractor
        ):
            if self.user not in config.get_host_specific_key(
                "groups.can_bypass_contractor_restrictions",
                host,
                [],
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")

        account_id = policy_arn.split(":")[4]
        policy_name = policy_arn.split("/")[-1]
        log_data = {
            "function": "ManagedPoliciesHandler.get",
            "user": self.user,
            "ip": self.ip,
            "message": "Retrieving managed policy",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "account_id": account_id,
            "policy_name": policy_name,
            "policy_arn": policy_arn,
        }

        log.debug(log_data)

        managed_policy_details = await aio_wrapper(
            get_managed_policy_document,
            policy_arn=policy_arn,
            account_number=account_id,
            assume_role=ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", host)
            .with_query({"account_id": account_id})
            .first.name,
            region=config.region,
            retry_max_attempts=2,
            client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
            host=host,
        )
        res = WebResponse(
            status=Status2.success,
            status_code=200,
            data=managed_policy_details,
        )
        self.write(res.json())


class ManagedPoliciesForAccountHandler(BaseAPIV2Handler):
    async def get(self, account_id):
        """
        Retrieve a list of managed policies for an account.
        """
        host = self.ctx.host
        if (
            config.get_host_specific_key(
                "policy_editor.disallow_contractors", host, True
            )
            and self.contractor
        ):
            if self.user not in config.get_host_specific_key(
                "groups.can_bypass_contractor_restrictions",
                host,
                [],
            ):
                raise MustBeFte("Only FTEs are authorized to view this page.")
        try:
            all_account_managed_policies = (
                await get_all_iam_managed_policies_for_account(account_id, host)
            )
        except Exception:
            sentry_sdk.capture_exception()
            all_account_managed_policies = []
        self.write(json.dumps(all_account_managed_policies))
