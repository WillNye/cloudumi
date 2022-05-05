import sys
from datetime import datetime, timedelta

import sentry_sdk
import ujson as json
from policy_sentry.util.arns import parse_arn

from common.config import config
from common.exceptions.exceptions import MustBeFte, ResourceNotFound
from common.handlers.base import BaseAPIV2Handler, BaseMtlsHandler
from common.lib.account_indexers import get_account_id_to_name_mapping
from common.lib.auth import can_admin_policies, get_accounts_user_can_view_resources_for
from common.lib.aws.utils import fetch_resource_details
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.plugins import get_plugin_by_name
from common.lib.policies import get_url_for_resource
from common.lib.redis import RedisHandler, redis_hget
from common.lib.web import handle_generic_error_response
from common.models import WebResponse

log = config.get_logger()
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()


class ResourceDetailHandler(BaseAPIV2Handler):
    async def get(self, account_id, resource_type, region=None, resource_name=None):
        if not self.user:
            return
        host = self.ctx.host
        red = await RedisHandler().redis(host)
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
        read_only = False

        can_save_delete = await can_admin_policies(
            self.user, self.groups, host, [account_id]
        )

        account_id_for_arn: str = account_id
        if resource_type == "s3":
            account_id_for_arn = ""
        arn = f"arn:aws:{resource_type}:{region or ''}:{account_id_for_arn}:{resource_name}"
        path = ""
        if resource_type == "managed_policy":
            # special case for managed policies
            path = region or ""
            if path:
                arn = f"arn:aws:iam::{account_id}:policy/{path}/{resource_name}"
            else:
                arn = f"arn:aws:iam::{account_id}:policy/{resource_name}"

        stats.count(
            "ResourcePolicyEditHandler.get",
            tags={
                "user": self.user,
                "arn": arn,
                "host": host,
            },
        )

        log_data = {
            "user": self.user,
            "ip": self.ip,
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Incoming request",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "arn": arn,
            "host": host,
        }

        log.debug(log_data)

        error = ""

        try:
            allowed_accounts_for_viewing_resources = (
                await get_accounts_user_can_view_resources_for(
                    self.user, self.groups, host
                )
            )
            if account_id not in allowed_accounts_for_viewing_resources:
                raise Exception(
                    f"User does not have permission to view resources for account {account_id}"
                )
            resource_details = await fetch_resource_details(
                account_id,
                resource_type,
                resource_name,
                region,
                host,
                self.user,
                path=path,
            )
        except Exception as e:
            sentry_sdk.capture_exception()
            log.error({**log_data, "error": e}, exc_info=True)
            resource_details = None
            error = str(e)

        if not resource_details:
            self.send_error(
                404,
                message=(
                    f"Unable to retrieve the specified {resource_type} resource: "
                    f"{account_id}/{resource_name}/{region}. {error}",
                ),
            )
            return

        # TODO: Get S3 errors for s3 buckets only, else CT errors
        yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
        s3_query_url = None
        if resource_type == "s3":
            s3_query_url = config.get_host_specific_key("s3.bucket_query_url", host)
        all_s3_errors = None
        if s3_query_url:
            s3_query_url = s3_query_url.format(
                yesterday=yesterday, bucket_name=f"'{resource_name}'"
            )
            s3_error_topic = config.get_host_specific_key(
                "redis.s3_errors", host, f"{host}_S3_ERRORS"
            )
            all_s3_errors = red.get(s3_error_topic)

        s3_errors = []
        if all_s3_errors:
            s3_errors = json.loads(all_s3_errors).get(arn, [])

        account_ids_to_name = await get_account_id_to_name_mapping(host)
        # TODO(ccastrapel/psanders): Make a Swagger spec for this
        self.write(
            dict(
                arn=arn,
                resource_details=resource_details,
                account_id=account_id,
                account_name=account_ids_to_name.get(account_id, None),
                read_only=read_only,
                can_save_delete=can_save_delete,
                s3_errors=s3_errors,
                error_url=s3_query_url,
                config_timeline_url=resource_details.get("config_timeline_url"),
            )
        )


class GetResourceURLHandler(BaseMtlsHandler):
    """consoleme CLI resource URL handler. Parameters accepted: arn."""

    def initialize(self):
        self.user: str = None
        self.eligible_roles: list = []

    async def get(self):
        """
        /api/v2/get_resource_url - Endpoint used to get an URL from an ARN
        ---
        get:
            description: Get the resource URL for ConsoleMe, given an ARN
            responses:
                200:
                    description: Returns a URL generated from the ARN in JSON form
                400:
                    description: Malformed Request
                403:
                    description: Forbidden
        """
        self.user: str = self.requester["email"]
        host = self.ctx.host
        red = await RedisHandler().redis(host)
        arn: str = self.get_argument("arn", None)
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "user": self.user,
            "arn": arn,
            "message": "Generating URL for resource",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
            "host": host,
        }
        log.debug(log_data)
        stats.count(
            "GetResourceURL.get",
            tags={
                "user": self.user,
                "host": host,
            },
        )
        if not arn:
            generic_error_message: str = "Missing required parameter"
            errors = ["arn is a required parameter"]
            await handle_generic_error_response(
                self, generic_error_message, errors, 404, "missing_data", log_data
            )
            return

        try:
            # parse_arn will raise an exception on invalid arns
            parse_arn(arn)

            resources_from_aws_config_redis_key = config.get_host_specific_key(
                "aws_config_cache.redis_key",
                host,
                f"{host}_AWSCONFIG_RESOURCE_CACHE",
            )
            if not red.exists(resources_from_aws_config_redis_key):
                # This will force a refresh of our redis cache if the data exists in S3
                await retrieve_json_data_from_redis_or_s3(
                    redis_key=resources_from_aws_config_redis_key,
                    s3_bucket=config.get_host_specific_key(
                        "aws_config_cache_combined.s3.bucket", host
                    ),
                    s3_key=config.get_host_specific_key(
                        "aws_config_cache_combined.s3.file",
                        host,
                        "aws_config_cache_combined/aws_config_resource_cache_combined_v1.json.gz",
                    ),
                    redis_data_type="hash",
                    host=host,
                )
            resource_info = await redis_hget(
                resources_from_aws_config_redis_key, arn, host
            )
            if not resource_info:
                raise ValueError("Resource not found in organization cache")
            resource_url = await get_url_for_resource(arn, host)
            if not resource_url:
                raise ValueError("This resource type is currently not supported")
        except (ResourceNotFound, ValueError) as e:
            generic_error_message: str = "Unsupported data"
            errors = [str(e)]
            await handle_generic_error_response(
                self, generic_error_message, errors, 404, "invalid_data", log_data
            )
            return
        except Exception as e:
            generic_error_message: str = "Malformed data"
            errors = [str(e)]
            await handle_generic_error_response(
                self, generic_error_message, errors, 404, "malformed_data", log_data
            )
            return

        res = WebResponse(
            status="success",
            status_code=200,
            message="Successfully generated URL for ARN",
            data={"url": resource_url},
        )

        self.write(res.json())
        await self.finish()
