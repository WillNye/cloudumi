import asyncio
import os
import sys
import time
import uuid
import zlib
from collections import defaultdict
from datetime import datetime

# used as a placeholder for empty SID to work around this:
# https://github.com/aws/aws-sdk-js/issues/833
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

import bcrypt
import sentry_sdk
import simplejson as json
import yaml
from asgiref.sync import sync_to_async
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import Binary  # noqa
from cloudaux import get_iso_string
from retrying import retry
from tenacity import Retrying, stop_after_attempt, wait_fixed

from common.config import config
from common.exceptions.exceptions import (
    DataNotRetrievable,
    NoExistingRequest,
    NoMatchingRequest,
    PendingRequestAlreadyExists,
)
from common.lib.assume_role import boto3_cached_conn
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.aws.session import (
    get_session_for_tenant,
    restricted_get_session_for_saas,
)
from common.lib.cache import retrieve_json_data_from_redis_or_s3
from common.lib.crypto import CryptoSign
from common.lib.dynamo.host_restrict_session_policy import get_session_policy_for_host
from common.lib.password import wait_after_authentication_failure
from common.lib.plugins import get_plugin_by_name
from common.lib.redis import RedisHandler
from common.lib.s3_helpers import get_s3_bucket_for_host
from common.models import AuthenticationResponse, ExtendedRequestModel
from identity.lib.groups.models import GroupRequest, GroupRequests

# TODO: Partion key should be host key. Dynamo instance should be retrieved dynamically. Should use dynamodb:LeadingKeys
# to restrict.
DYNAMO_EMPTY_STRING = "---DYNAMO-EMPTY-STRING---"

# We need to import Decimal to eval the request. This Decimal usage is to prevent lint errors on importing the unused
# Decimal module.
DYNAMODB_EMPTY_DECIMAL = Decimal(0)

POSSIBLE_STATUSES = [
    "pending",
    "approved",
    "cancelled",
    "expired",
    "removed",
]

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()
log = config.get_logger("consoleme")


async def hash_api_key(api_key, user, host) -> str:
    """
    Hashes an API key.
    """
    import base64
    import hashlib
    import hmac

    return base64.b64encode(
        hmac.new(
            api_key.encode("utf-8"),
            f"{user}:{host}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")


class BaseDynamoHandler:
    """Base class for interacting with DynamoDB."""

    def _get_dynamo_table(self, table_name, host):
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )

        # TODO: Support getting DynamoDB table in customer accounts through nested assume role calls
        restrictive_session_policy = get_session_policy_for_host(host)

        try:
            # call sts_conn with my client and pass in forced_client
            if config.get("_global_.dynamodb_server"):
                session = get_session_for_tenant(host)
                resource = session.resource(
                    "dynamodb",
                    region_name=config.region,
                    endpoint_url=config.get(
                        "_global_.dynamodb_server",
                        config.get("_global_.boto3.client_kwargs.endpoint_url"),
                    ),
                )
            else:
                resource = boto3_cached_conn(
                    "dynamodb",
                    host,
                    service_type="resource",
                    account_number=config.get_host_specific_key(
                        f"site_configs.{host}.aws.account_number", host
                    ),
                    session_name=sanitize_session_name("consoleme_dynamodb"),
                    region=config.region,
                    client_kwargs=config.get("_global_.boto3.client_kwargs", {}),
                    session_policy=restrictive_session_policy,
                    # TODO: This implies only hosting data in SaaS and not customer env. We will need to change this
                    # to support data plane in customer env
                    pre_assume_roles=[],
                )
            table = resource.Table(table_name)
            return table
        except Exception as e:
            log.error(
                {
                    "function": function,
                    "error": e,
                    "host": host,
                },
                exc_info=True,
            )
            stats.count(f"{function}.exception")
            return None
        else:
            return table

    def _data_from_dynamo_replace(
        self,
        obj: Union[
            List[Dict[str, Union[Decimal, str]]],
            Dict[str, Union[Decimal, str]],
            str,
            Decimal,
        ],
    ) -> Union[int, Dict[str, Union[int, str]], str, List[Dict[str, Union[int, str]]]]:
        """Traverse a potentially nested object and replace all Dynamo placeholders with actual empty strings
        Args:
            obj (object)
        Returns:
            object: Object with original empty strings
        """
        if isinstance(obj, dict):
            for k in ["aws:rep:deleting", "aws:rep:updateregion", "aws:rep:updatetime"]:
                if k in obj.keys():
                    del obj[k]
            return {k: self._data_from_dynamo_replace(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._data_from_dynamo_replace(elem) for elem in obj]
        else:
            if isinstance(obj, Binary):
                obj = obj.value
            if str(obj) == DYNAMO_EMPTY_STRING:
                obj = ""
            elif isinstance(obj, Decimal):
                obj = int(obj)
            return obj

    def _data_to_dynamo_replace(self, obj: Any) -> Any:
        """Traverse a potentially nested object and replace all instances of an empty string with a placeholder
        Args:
            obj (object)
        Returns:
            object: Object with Dynamo friendly empty strings
        """
        if isinstance(obj, dict):
            for k in ["aws:rep:deleting", "aws:rep:updateregion", "aws:rep:updatetime"]:
                if k in obj.keys():
                    del obj[k]
            return {k: self._data_to_dynamo_replace(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._data_to_dynamo_replace(elem) for elem in obj]
        else:
            if isinstance(obj, Binary):
                return obj
            if str(obj) == "":
                obj = DYNAMO_EMPTY_STRING
            elif type(obj) in [float, int]:
                obj = Decimal(str(obj))
            elif isinstance(obj, datetime):
                obj = Decimal(str(obj.timestamp()))
            return obj

    def parallel_write_table(self, table, data, overwrite_by_pkeys=None):
        if not overwrite_by_pkeys:
            overwrite_by_pkeys = []
        with table.batch_writer(overwrite_by_pkeys=overwrite_by_pkeys) as batch:
            for item in data:
                for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(2)):
                    with attempt:
                        batch.put_item(Item=self._data_to_dynamo_replace(item))

    def parallel_delete_table_entries(self, table, keys):
        with table.batch_writer() as batch:
            for key in keys:
                for attempt in Retrying(stop=stop_after_attempt(3), wait=wait_fixed(2)):
                    with attempt:
                        batch.delete_item(Key=self._data_to_dynamo_replace(key))

    def parallel_scan_table(
        self,
        table,
        total_threads=os.cpu_count(),
        dynamodb_kwargs: Optional[Dict[str, Any]] = None,
    ):
        if not dynamodb_kwargs:
            dynamodb_kwargs = {}

        async def _scan_segment(segment, total_segments):
            response = table.scan(
                Segment=segment, TotalSegments=total_segments, **dynamodb_kwargs
            )
            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                    Segment=segment,
                    TotalSegments=total_segments,
                    **dynamodb_kwargs,
                )
                items.extend(self._data_from_dynamo_replace(response["Items"]))

            return items

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tasks = []
        for i in range(total_threads):
            task = asyncio.ensure_future(_scan_segment(i, total_threads))
            tasks.append(task)

        results = loop.run_until_complete(asyncio.gather(*tasks))
        items = []
        for result in results:
            items.extend(result)
        return items

    async def parallel_scan_table_async(
        self,
        table,
        total_threads=os.cpu_count(),
        dynamodb_kwargs: Optional[Dict[str, Any]] = None,
    ):
        if not dynamodb_kwargs:
            dynamodb_kwargs = {}

        async def _scan_segment(segment, total_segments):
            response = table.scan(
                Segment=segment, TotalSegments=total_segments, **dynamodb_kwargs
            )
            items = response.get("Items", [])

            while "LastEvaluatedKey" in response:
                response = table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                    Segment=segment,
                    TotalSegments=total_segments,
                    **dynamodb_kwargs,
                )
                items.extend(self._data_from_dynamo_replace(response["Items"]))

            return items

        tasks = []
        for i in range(total_threads):
            task = asyncio.ensure_future(_scan_segment(i, total_threads))
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        items = []
        for result in results:
            items.extend(result)
        return items

    def truncateTable(self, table, host):
        """
        Truncate a dynamo table - For development
        """
        # get the table keys
        tableKeyNames = [key.get("AttributeName") for key in table.key_schema]

        # Only retrieve the keys for each item in the table (minimize data transfer)
        projectionExpression = ", ".join("#" + key for key in tableKeyNames)
        expressionAttrNames = {"#" + key: key for key in tableKeyNames}
        filterExpression = Key("host").eq(host)

        counter = 0
        page = table.scan(
            ProjectionExpression=projectionExpression,
            ExpressionAttributeNames=expressionAttrNames,
            FilterExpression=filterExpression,
        )
        with table.batch_writer() as batch:
            while page["Count"] > 0:
                counter += page["Count"]
                # Delete items in batches
                for itemKeys in page["Items"]:
                    batch.delete_item(Key=itemKeys)
                # Fetch the next page
                if "LastEvaluatedKey" in page:
                    page = table.scan(
                        ProjectionExpression=projectionExpression,
                        ExpressionAttributeNames=expressionAttrNames,
                        ExclusiveStartKey=page["LastEvaluatedKey"],
                    )
                else:
                    break


class UserDynamoHandler(BaseDynamoHandler):
    def __init__(self, host, user: Optional[str] = None) -> None:
        self.host = host
        try:
            self.identity_requests_table = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.requests_dynamo_table",
                    host,
                    "consoleme_identity_requests_multitenant",
                ),
                host,
            )
            self.users_table = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.users_dynamo_table",
                    host,
                    "consoleme_users_multitenant",
                ),
                host,
            )
            self.group_log = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.group_log_dynamo_table",
                    host,
                    "consoleme_audit_global",
                ),
                host,
            )
            self.dynamic_config = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.dynamic_config_dynamo_table",
                    host,
                    "consoleme_config_multitenant",
                ),
                host,
            )
            self.policy_requests_table = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.policy_requests_dynamo_table",
                    host,
                    "consoleme_policy_requests_multitenant",
                ),
                host,
            )
            self.resource_cache_table = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.resource_cache_dynamo_table",
                    host,
                    "consoleme_resource_cache_multitenant",
                ),
                host,
            )
            self.cloudtrail_table = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.cloudtrail_table",
                    host,
                    "consoleme_cloudtrail_multitenant",
                ),
                host,
            )

            self.notifications_table = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.notifications_table",
                    host,
                    "consoleme_notifications_multitenant",
                ),
                host,
            )

            self.identity_groups_table = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.identity_groups_table",
                    host,
                    "consoleme_identity_groups_multitenant",
                ),
                host,
            )

            self.identity_users_table = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.identity_users_table",
                    host,
                    "consoleme_identity_users_multitenant",
                ),
                host,
            )

            self.tenant_static_configs = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.tenant_static_config_table",
                    host,
                    "consoleme_tenant_static_configs",
                ),
                host,
            )

            self.noq_api_keys = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.noq_api_keys_table",
                    host,
                    "noq_api_keys",
                ),
                host,
            )

            if user and host:
                self.user = self.get_or_create_user(user, host)
                self.affected_user = self.user
        except Exception:
            if config.get("_global_.development"):
                log.error(
                    {
                        "message": "Unable to connect to Dynamo. Trying to set user via development configuration",
                        "host": host,
                    },
                    exc_info=True,
                )
                self.user = self.sign_request(
                    {
                        "host": host,
                        "last_updated": int(time.time()),
                        "username": user,
                        "requests": [],
                    },
                    host=host,
                )
                self.affected_user = self.user
            else:
                log.error(
                    {
                        "message": "Unable to get Dynamo table.",
                        "host": host,
                    },
                    exc_info=True,
                )
                raise

    async def create_api_key(self, user, host, ttl=None) -> str:
        """
        Creates a new API key for the user.
        :param user: The user to create an API key for.
        :param host: The host to create the API key for.
        :param ttl: The TTL for the API key.
        :return: The API key.
        """

        async def generate_api_key() -> str:
            """
            Generates an API key.
            """
            import secrets

            return secrets.token_hex(32)

        # Create a new API key
        api_key = await generate_api_key()
        hashed_api_key = await hash_api_key(api_key, user, host)

        # Store hashed API Key in Dynamo
        await sync_to_async(self.noq_api_keys.put_item)(
            Item={
                "host": host,
                "user": user,
                "api_key": hashed_api_key,
                "id": str(uuid.uuid4()),
                "ttl": ttl,
            }
        )

        return api_key

    async def verify_api_key(self, api_key, user, host) -> bool:
        """
        Verifies an API key.
        :param api_key: The API key to verify.
        :param user: The user to verify the API key for.
        :param host: The host to verify the API key for.
        :return: True if the API key is valid, False otherwise.
        """
        hashed_api_key = await hash_api_key(api_key, user, host)
        # Get the hashed API key
        hashed_api_entry = await sync_to_async(self.noq_api_keys.get_item)(
            Key={"host": host, "api_key": hashed_api_key}
        )

        # Verify the API key
        if hashed_api_entry.get("Item"):
            if not hashed_api_entry["Item"]["user"] == user:
                return False
            return user
        return False

    async def delete_api_key(self, host, user, api_key=None, api_key_id=None):
        """
        Delete API Key from Dynamo
        """
        if api_key:
            hashed_api_key = await hash_api_key(api_key, user, host)
            await self.noq_api_keys.delete_item(
                Key={"host": host, "api_key": hashed_api_key}
            )
            return True
        elif api_key_id:
            res = await sync_to_async(self.cloudtrail_table.query)(
                IndexName="host_id_index",
                KeyConditionExpression="id = :id AND host = :h",
                ExpressionAttributeValues={":id": api_key_id, ":h": host},
            )
            items = res.get("Items", [])
            for item in items:
                await self.noq_api_keys.delete_item(
                    Key={"host": host, "api_key": item["api_key"]}
                )
                return True

    async def get_static_config_for_host(self, host) -> bytes:
        """Retrieve dynamic configuration yaml asynchronously"""
        c = b""
        try:
            current_config = await sync_to_async(self.tenant_static_configs.get_item)(
                Key={"host": host, "id": "master"}
            )
            if not current_config:
                return c
            compressed_config = current_config.get("Item", {}).get("config", "")
            if not compressed_config:
                return c
            c = zlib.decompress(compressed_config.value)
        except Exception as e:  # noqa
            log.error(
                {
                    "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                    "message": "Error retrieving static configuration",
                    "error": str(e),
                }
            )
            sentry_sdk.capture_exception()
        return c

    def write_resource_cache_data(self, data):
        self.parallel_write_table(
            self.resource_cache_table, data, ["resourceId", "resourceType"]
        )

    async def get_dynamic_config_yaml(self, host) -> bytes:
        """Retrieve dynamic configuration yaml."""
        return await sync_to_async(self.get_dynamic_config_yaml_sync)(host)

    def get_dynamic_config_yaml_sync(self, host) -> bytes:
        """Retrieve dynamic configuration yaml synchronously"""
        c = b""
        try:
            current_config = self.dynamic_config.get_item(
                Key={"host": host, "id": "master"}
            )
            if not current_config:
                return c
            compressed_config = current_config.get("Item", {}).get("config", "")
            if not compressed_config:
                return c
            c = zlib.decompress(compressed_config.value)
        except Exception as e:  # noqa
            log.error(
                {
                    "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                    "message": "Error retrieving dynamic configuration",
                    "host": host,
                    "error": str(e),
                }
            )
            sentry_sdk.capture_exception()
        return c

    def get_dynamic_config_dict(self, host) -> dict:
        """Retrieve dynamic configuration dictionary that can be merged with primary configuration dictionary."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # if cleanup: 'RuntimeError: There is no current event loop..'
            loop = None
        if loop and loop.is_running():
            current_config_yaml = self.get_dynamic_config_yaml_sync(host)
        else:
            current_config_yaml = asyncio.run(self.get_dynamic_config_yaml(host))
        config_d = yaml.safe_load(current_config_yaml)
        return config_d

    async def write_policy_request_v2(
        self, extended_request: ExtendedRequestModel, host: str
    ):
        """
        Writes a policy request v2 to the appropriate DynamoDB table
        Sample run:
        write_policy_request_v2(request)
        """
        new_request = {
            "request_id": extended_request.id,
            "principal": extended_request.principal.dict(),
            "status": extended_request.request_status.value,
            "justification": extended_request.justification,
            "request_time": extended_request.timestamp,
            "last_updated": int(time.time()),
            "version": "2",
            "extended_request": json.loads(extended_request.json()),
            "username": extended_request.requester_email,
            "host": host,
        }

        if extended_request.principal.principal_type == "AwsResource":
            new_request["arn"] = extended_request.principal.principal_arn
        elif extended_request.principal.principal_type == "HoneybeeAwsResourceTemplate":
            repository_name = extended_request.principal.repository_name
            resource_identifier = extended_request.principal.resource_identifier
            new_request["arn"] = f"{repository_name}-{resource_identifier}"
        else:
            raise Exception("Invalid principal type")

        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Writing policy request v2 to Dynamo",
            "request": new_request,
            "host": host,
        }
        log.debug(log_data)

        try:
            await sync_to_async(self.policy_requests_table.put_item)(
                Item=self._data_to_dynamo_replace(new_request)
            )
            log_data[
                "message"
            ] = "Successfully finished writing policy request v2 to Dynamo"
            log.debug(log_data)
        except Exception as e:
            log_data["message"] = "Error occurred writing policy request v2 to Dynamo"
            log_data["error"] = str(e)
            log.error(log_data, exc_info=True)
            error = f"{log_data['message']}: {str(e)}"
            raise Exception(error)

        return new_request

    async def get_policy_requests(self, host: str, arn=None, request_id=None):
        """Reads a policy request from the appropriate DynamoDB table"""
        if not arn and not request_id:
            raise Exception("Must pass in ARN or policy request ID")
        if request_id:
            requests = self.policy_requests_table.query(
                KeyConditionExpression="request_id = :ri AND host = :h",
                ExpressionAttributeValues={":ri": request_id, ":h": host},
            )
        else:
            requests = self.policy_requests_table.query(
                KeyConditionExpression="arn = :arn AND host = :h",
                ExpressionAttributeValues={":arn": arn, ":h": host},
            )
        matching_requests = []
        if requests["Items"]:
            items = self._data_from_dynamo_replace(requests["Items"])
            matching_requests.extend(items)
        return matching_requests

    async def get_all_policy_requests(
        self, host: str, status: Optional[str] = "pending"
    ) -> List[Dict[str, Union[int, List[str], str]]]:
        """Return all policy requests. If a status is specified, only requests with the specified status will be
        returned.
        :param status:
        :return:
        """
        # TODO: Index by host instead of scanning
        requests = await sync_to_async(self.parallel_scan_table)(
            self.policy_requests_table
        )

        return_value = []
        for item in requests:
            if not item["host"] == host:
                continue
            if status and not item["status"] == status:
                continue
            return_value.append(item)
        return return_value

    async def update_dynamic_config(
        self,
        new_config: str,
        updated_by: str,
        host: str,
    ) -> None:
        """Take a YAML config and writes to DDB (The reason we use YAML instead of JSON is to preserve comments)."""
        # Validate that config loads as yaml, raises exception if not
        yaml.safe_load(new_config)
        stats.count("update_dynamic_config", tags={"updated_by": updated_by})
        current_config_entry = self.dynamic_config.get_item(
            Key={"host": host, "id": "master"}
        )
        if current_config_entry.get("Item"):
            old_config = {
                "host": host,
                "id": current_config_entry["Item"]["updated_at"],
                "updated_by": current_config_entry["Item"]["updated_by"],
                "config": current_config_entry["Item"]["config"],
                "updated_at": str(int(time.time())),
            }

            self.dynamic_config.put_item(Item=self._data_to_dynamo_replace(old_config))

        new_config_writable = {
            "host": host,
            "id": "master",
            "config": zlib.compress(new_config.encode()),
            "updated_by": updated_by,
            "updated_at": str(int(time.time())),
        }
        self.dynamic_config.put_item(
            Item=self._data_to_dynamo_replace(new_config_writable)
        )

    # def validate_signature(self, items):
    #     signature = items.pop("signature")
    #     if isinstance(signature, Binary):
    #         signature = signature.value
    #     json_request = json.dumps(items, sort_keys=True)
    #     if not crypto.verify(json_request, signature):
    #         raise Exception(f"Invalid signature for request: {json_request}")

    def sign_request(
        self, user_entry: Dict[str, Union[Decimal, List[str], Binary, str]], host: str
    ) -> Dict[str, Union[Decimal, List[str], str, bytes]]:
        """
        Sign the request and returned request with signature
        :param user_entry:
        :return:
        """
        crypto = CryptoSign(host)
        # Remove old signature if it exists
        user_entry.pop("signature", None)
        user_entry = self._data_from_dynamo_replace(user_entry)
        json_request = json.dumps(user_entry, sort_keys=True, use_decimal=True)
        sig = crypto.sign(json_request)
        user_entry["signature"] = sig
        return user_entry

    async def authenticate_user(self, login_attempt, host) -> AuthenticationResponse:
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "user_email": login_attempt.username,
            "after_redirect_uri": login_attempt.after_redirect_uri,
            "host": host,
        }
        user_entry = await sync_to_async(self.users_table.query)(
            KeyConditionExpression="username = :un AND host = :h",
            ExpressionAttributeValues={":un": login_attempt.username, ":h": host},
        )
        user = None

        generic_error = ["User doesn't exist, or password is incorrect. "]

        if user_entry and "Items" in user_entry and len(user_entry["Items"]) == 1:
            user = user_entry["Items"][0]
        if not user:
            delay_error = await wait_after_authentication_failure(
                login_attempt.username, host
            )
            error = f"Unable to find user: {login_attempt.username}"
            log.error({**log_data, "message": error + delay_error})
            return AuthenticationResponse(
                authenticated=False, errors=generic_error + [delay_error]
            )

        if not user.get("password"):
            delay_error = await wait_after_authentication_failure(
                login_attempt.username, host
            )
            error = "User exists, but doesn't have a password stored in the database"
            log.error({**log_data, "message": error + delay_error})
            return AuthenticationResponse(
                authenticated=False, errors=generic_error + [delay_error]
            )

        password_hash_matches = bcrypt.checkpw(
            login_attempt.password.encode("utf-8"), user["password"].value
        )
        if not password_hash_matches:
            delay_error = await wait_after_authentication_failure(
                login_attempt.username, host
            )
            error = "Password does not match. "
            log.error({**log_data, "message": error + delay_error})
            return AuthenticationResponse(
                authenticated=False, errors=generic_error + [delay_error]
            )
        return AuthenticationResponse(
            authenticated=True, username=user["username"], groups=user["groups"]
        )

    def create_user(
        self,
        user_email: str,
        host: str,
        password: Optional[str] = None,
        groups: Optional[List[str]] = None,
    ):
        if not groups:
            groups = []
        timestamp = int(time.time())
        unsigned_user_entry = {
            "created": timestamp,
            "last_updated": timestamp,
            "username": user_email,
            "requests": [],
            "groups": groups,
            "host": host,
        }

        if password:
            pw = bytes(password, "utf-8")
            salt = bcrypt.gensalt()
            unsigned_user_entry["password"] = bcrypt.hashpw(pw, salt)

        user_entry = self.sign_request(unsigned_user_entry, host)
        try:
            self.users_table.put_item(Item=self._data_to_dynamo_replace(user_entry))
        except Exception as e:
            error = f"Unable to add user submission: {user_entry}: {str(e)}"
            log.error(error, exc_info=True)
            raise Exception(error)
        return user_entry

    def update_user(
        self,
        user_email,
        host,
        password: Optional[str] = None,
        groups: Optional[List[str]] = None,
    ):
        if not groups:
            groups = []

        user_ddb = self.users_table.query(
            KeyConditionExpression="username = :un AND host = :h",
            ExpressionAttributeValues={":un": user_email, ":h": host},
        )

        user = None

        if user_ddb and "Items" in user_ddb and len(user_ddb["Items"]) == 1:
            user = user_ddb["Items"][0]

        if not user:
            raise DataNotRetrievable(f"Unable to find user: {user_email}")

        timestamp = int(time.time())

        if password:
            pw = bytes(password, "utf-8")
            salt = bcrypt.gensalt()
            user["password"] = bcrypt.hashpw(pw, salt)

        if groups:
            user["groups"] = groups
        user["last_updated"] = timestamp
        user["host"] = host

        user_entry = self.sign_request(user, host)
        try:
            self.users_table.put_item(Item=self._data_to_dynamo_replace(user_entry))
        except Exception as e:
            error = f"Unable to add user submission: {user_entry}: {str(e)}"
            log.error(error, exc_info=True)
            raise Exception(error)
        return user_entry

    def delete_user(self, user_email, host):
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "user_email": user_email,
            "host": host,
        }
        log.debug(log_data)
        user_entry = {"username": user_email, "host": host}
        try:
            self.users_table.delete_item(Key=self._data_to_dynamo_replace(user_entry))
        except Exception as e:
            error = f"Unable to delete user: {user_entry}: {str(e)}"
            log.error(error, exc_info=True)
            raise Exception(error)

    async def get_user(
        self, user_email: str, host: str
    ) -> Optional[Dict[str, Union[Decimal, List[str], Binary, str]]]:
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "user_email": user_email,
            "host": host,
        }

        log.debug(log_data)

        user = self.users_table.query(
            KeyConditionExpression="username = :un AND host = :h",
            ExpressionAttributeValues={":un": user_email, ":h": host},
        )

        if user and "Items" in user and len(user["Items"]) == 1:
            return user["Items"][0]
        return None

    def get_or_create_user(
        self, user_email: str, host: str
    ) -> Dict[str, Union[Decimal, List[str], Binary, str]]:
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "user_email": user_email,
            "host": host,
        }

        log.debug(log_data)

        user = self.users_table.query(
            KeyConditionExpression="username = :un AND host = :h",
            ExpressionAttributeValues={":un": user_email, ":h": host},
        )

        items = []

        if user and "Items" in user:
            items = user["Items"]

        if not items:
            return self.create_user(user_email, host)
        return items[0]

    def resolve_request_ids(
        self, request_ids: List[str], host: str
    ) -> List[Dict[str, Union[int, str]]]:
        requests = []
        for request_id in request_ids:
            request = self.identity_requests_table.query(
                KeyConditionExpression="request_id = :ri AND host = :h",
                ExpressionAttributeValues={":ri": request_id, ":h": host},
            )

            if request["Items"]:
                items = self._data_from_dynamo_replace(request["Items"])
                requests.append(items[0])
            else:
                raise NoMatchingRequest(
                    f"No matching request for request_id: {request_id} and host: {host}"
                )
        return requests

    def add_request_id_to_user(
        self,
        affected_user: Dict[str, Union[Decimal, List[str], Binary, str]],
        request_id: str,
        host: str,
    ) -> None:
        if affected_user["host"] != host:
            raise Exception(
                "Host associated with user is different than the host the user authenticated with"
            )
        affected_user["requests"].append(request_id)
        self.users_table.put_item(
            Item=self._data_to_dynamo_replace(self.sign_request(affected_user, host))
        )

    def add_request(
        self,
        user_email: str,
        group: str,
        justification: str,
        host: str,
        request_time: None = None,
        status: str = "pending",
        updated_by: Optional[str] = None,
    ) -> Dict[str, Union[int, str]]:
        """
        Add a user request to the dynamo table
        Sample run:
        add_request("user@example.com", "engtest", "because")
        :param user_email: Email address of user
        :param group: Name of group user is requesting access to
        :param justification:
        :param request_id:
        :param request_time:
        :param status:
        :param updated_by:
        :return:
        """
        """
        Request:
          group
          justification
          role
          request_time
          approval_time
          updated_by
          approval_reason
          status
        user@example.com:
          requests: []
          last_updated: 1
          signature: xxxx
        #pending: []
        #expired: []
        # How to expire requests if soemeone maliciously deletes content
        # How to query for all approved requests for group X
        # What if we want to send email saying your request is expiring in 7 days? Maybe celery to query all
        # What about concept of request ID? Maybe base64 encoded thing?
        # Need an all-in-one page to show all pending requests, all expired/approved requests
      """
        request_time = request_time or int(time.time())

        stats.count("new_group_request", tags={"user": user_email, "group": group})

        if self.affected_user.get("username") != user_email:
            self.affected_user = self.get_or_create_user(user_email, host)
        # Get current user. Create if they do not already exist
        # self.user = self.get_or_create_user(user_email)
        # Get current user requests, which will validate existing signature
        # existing_request_ids = self.user["requests"]
        # existing_requests = self.resolve_request_ids(existing_request_ids)
        existing_pending_requests_for_group = self.get_requests_by_user(
            user_email, host, group=group, status="pending"
        )

        # Craft the new request json
        timestamp = int(time.time())
        request_id = str(uuid.uuid4())
        new_request = {
            "request_id": request_id,
            "group": group,
            "status": status,
            "justification": justification,
            "request_time": request_time,
            "updated_by": updated_by,
            "last_updated": timestamp,
            "username": user_email,
            "host": host,
        }

        # See if user already has an active or pending request for the group
        if existing_pending_requests_for_group:
            for request in existing_pending_requests_for_group:
                raise PendingRequestAlreadyExists(
                    f"Pending request for group: {group} already exists: {request}"
                )
        try:
            self.identity_requests_table.put_item(
                Item=self._data_to_dynamo_replace(new_request)
            )
        except Exception as e:
            error = {
                "error": f"Unable to add user request: {str(e)}",
                "request": new_request,
            }
            log.error(error, exc_info=True)
            raise Exception(error)

        self.add_request_id_to_user(self.affected_user, request_id, host)

        return new_request

    async def get_identity_group_request_by_id(self, host, request_id):
        response: Dict = await sync_to_async(self.identity_requests_table.query)(
            KeyConditionExpression="request_id = :ri AND host = :h",
            ExpressionAttributeValues={":ri": request_id, ":h": host},
        )
        items = response.get("Items", [])
        if not items:
            return None
        if len(items) > 1:
            raise Exception(f"Multiple requests found for request_id: {request_id}")
        return self._data_from_dynamo_replace(items[0])

    async def get_all_identity_group_requests(self, host: str, status=None):
        """Return all requests. If a status is specified, only requests with the specified status will be returned.
        :param status:
        :return:
        """
        items = await sync_to_async(self.parallel_scan_table)(
            self.identity_requests_table
        )

        return_value = []
        for item in items:
            if status and not item["status"] == status:
                continue
            if item["host"] != host:
                continue
            return_value.append(self._data_from_dynamo_replace(item))
        return return_value

    async def get_identity_group_requests_by_user(
        self,
        user_email: str,
        host: str,
        group: str = None,
        idp: str = None,
        status: str = None,
    ) -> Union[List[Dict[str, Union[int, str]]], Any]:
        """Get requests by user. Group and status can also be specified to filter results.
        :param user_email:
        :param group:
        :param status:
        :return:
        """
        red = RedisHandler().redis_sync(host)
        # TODO: Use cache
        red_key = f"{host}_GROUP_IDENTITY_REQUESTS"

        requests_to_return = []
        requests = []
        requests_j = red.hget(red_key, user_email)

        requests_j = await retrieve_json_data_from_redis_or_s3(
            redis_key=red_key,
            redis_data_type="hash",
            s3_bucket=await get_s3_bucket_for_host(host),
            redis_field=user_email,
            host=host,
            default="[]",
        )
        if requests_j:
            requests = GroupRequests(requests=json.loads(requests_j))
        for request in requests.requests:
            user_in_request = False
            for user in request.users:
                if user.username == user_email:
                    user_in_request = True
                    break
            if not user_in_request:
                continue
            group_in_request = True if not group else False
            for request_group in request.groups:
                if request_group.group == group and request_group.idp == idp:
                    group_in_request = True
                    break
            if not group_in_request:
                continue
            if status and request.status.value != status:
                continue
            requests_to_return.append(request)
        return requests_to_return

    async def create_identity_group_request(
        self, host, user_email, request: GroupRequest
    ) -> GroupRequest:
        """Create a new group request.
        :param request:
        :return:
        """
        from common.celery_tasks.celery_tasks import app as celery_app

        request_dict = json.loads(request.json())
        self.identity_requests_table.put_item(
            Item=self._data_to_dynamo_replace(request_dict)
        )
        celery_app.send_task(
            "cloudumi_common.celery_tasks.celery_tasks.cache_identity_group_requests_for_host_t",
            kwargs={"host": host},
        )

        return request

    async def get_pending_identity_group_requests(
        self, host, user=None, group=None, idp=None, status=None
    ):
        """
        Get all pending identity group requests.
        :param host:
        :param user:
        :param group:
        :param status:
        :return:
        """
        if user:
            return await self.get_identity_group_requests_by_user(
                user,
                host,
                group=group,
                idp=idp,
                status=status,
            )
        else:
            return await self.get_all_identity_group_requests(host, status=status)

    def change_request_status(
        self,
        user_email,
        group,
        new_status,
        host,
        updated_by=None,
        reviewer_comments=None,
    ):
        """
        :param user:
        :param status:
        :param request_id:
        :return:
        """
        stats.count(
            "update_group_request",
            tags={
                "user": user_email,
                "group": group,
                "new_status": new_status,
                "updated_by": updated_by,
                "host": host,
            },
        )
        modified_request = None
        if self.affected_user.get("username") != user_email:
            self.affected_user = self.get_or_create_user(user_email, host)
        timestamp = int(time.time())
        if new_status not in POSSIBLE_STATUSES:
            raise Exception(
                f"Invalid status. Status must be one of {POSSIBLE_STATUSES}"
            )
        if new_status == "approved" and not updated_by:
            raise Exception(
                "You must provide `updated_by` to change a request status to approved."
            )
        existing_requests = self.get_requests_by_user(user_email, host)
        if existing_requests:
            updated = False
            for request in existing_requests:
                if request["group"] == group:
                    request["updated_by"] = updated_by
                    request["status"] = new_status
                    request["last_updated"] = timestamp
                    request["reviewer_comments"] = reviewer_comments
                    request["host"] = host
                    modified_request = request
                    try:
                        self.identity_requests_table.put_item(
                            Item=self._data_to_dynamo_replace(request)
                        )
                    except Exception as e:
                        error = f"Unable to add user request: {request}: {str(e)}"
                        log.error(error, exc_info=True)
                        raise Exception(error)
                    updated = True

            if not updated:
                raise NoExistingRequest(
                    f"Unable to find existing request for user: {user_email} and group: {group}."
                )
        else:
            raise NoExistingRequest(
                f"Unable to find existing requests for user: {user_email}"
            )

        return modified_request

    async def change_request_status_by_id(
        self,
        host: str,
        request_id: str,
        new_status: str,
        updated_by: Optional[str] = None,
        reviewer_comments: Optional[str] = None,
        expiration: Optional[int] = None,
    ) -> Dict[str, Union[int, str]]:
        """
        Change request status by ID
        :param request_id:
        :param new_status:
        :param updated_by:
        :return: new requests
        """
        modified_request = None
        if new_status == "approved" and not updated_by:
            raise Exception(
                "You must provide `updated_by` to change a request status to approved."
            )
        requests = self.resolve_request_ids([request_id], host)

        if new_status not in POSSIBLE_STATUSES:
            raise Exception(
                f"Invalid status. Status must be one of {POSSIBLE_STATUSES}"
            )

        for request in requests:
            request["status"] = new_status
            request["updated_by"] = updated_by
            request["last_updated_time"] = int(time.time())
            request["reviewer_comments"] = reviewer_comments
            request["expiration"] = expiration
            request["host"] = host
            modified_request = request
            try:
                self.identity_requests_table.put_item(
                    Item=self._data_to_dynamo_replace(request)
                )
            except Exception as e:
                error = f"Unable to add user request: {request} : {str(e)}"
                log.error(error, exc_info=True)
                raise Exception(error)
        return modified_request

    async def create_group_log_entry(
        self,
        group: str,
        username: str,
        updated_by: str,
        action: str,
        host: str,
        updated_at: None = None,
        extra: None = None,
    ) -> None:
        updated_at = updated_at or int(time.time())

        log_id = str(uuid.uuid4())
        log_entry = {
            "uuid": log_id,
            "group": group,
            "username": username,
            "updated_by": updated_by,
            "updated_at": updated_at,
            "action": action,
            "extra": extra,
            "host": host,
        }
        self.group_log.put_item(Item=self._data_to_dynamo_replace(log_entry))

    def batch_write_cloudtrail_events(self, items, host: str):
        with self.cloudtrail_table.batch_writer(
            overwrite_by_pkeys=["host", "request_id"]
        ) as batch:
            for item in items:
                batch.put_item(Item=self._data_to_dynamo_replace(item))
        return True

    async def get_top_cloudtrail_errors_by_arn(self, arn, host, n=5):
        response: dict = await sync_to_async(self.cloudtrail_table.query)(
            IndexName="host-arn-index",
            KeyConditionExpression="arn = :arn AND host = :h",
            ExpressionAttributeValues={":arn": arn, ":h": host},
        )
        items = response.get("Items", [])
        aggregated_errors = defaultdict(dict)

        for item in items:
            if int(item["ttl"]) < int(time.time()):
                continue
            event_call = item["event_call"]
            event_resource = item.get("resource", "")

            event_string = f"{event_call}|||{event_resource}"
            if not aggregated_errors.get(event_string):
                aggregated_errors[event_string]["count"] = 0
                aggregated_errors[event_string]["generated_policy"] = item.get(
                    "generated_policy", {}
                )
            aggregated_errors[event_string]["count"] += 1

        top_n_errors = {
            k: v
            for k, v in sorted(
                aggregated_errors.items(),
                key=lambda item: item[1]["count"],
                reverse=True,
            )[:n]
        }

        return top_n_errors

    def count_arn_errors(self, error_count, items):
        for item in items:
            arn = item.get("arn")
            if not error_count.get(arn):
                error_count[arn] = 0
            error_count[arn] += item.get("count", 1)
        return error_count

    def fetch_groups_for_host(self, host):
        # TODO: Support filtering?
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "host": host,
        }

        log.debug(log_data)
        groups = self.identity_groups_table.query(
            KeyConditionExpression="host = :h",
            ExpressionAttributeValues={":h": host},
        )
        return groups

    def fetch_users_for_host(self, host):
        # TODO: Support filtering?
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        log_data = {
            "function": function,
            "host": host,
        }

        log.debug(log_data)
        users = self.identity_users_table.query(
            KeyConditionExpression="host = :h",
            ExpressionAttributeValues={":h": host},
        )
        return users


class RestrictedDynamoHandler(BaseDynamoHandler):
    def __init__(self) -> None:
        self.tenant_static_configs = self._get_dynamo_table_restricted(
            config.get(
                "_global_.aws.tenant_static_config_dynamo_table",
                "consoleme_tenant_static_configs",
            )
        )

    def _get_dynamo_table_restricted(self, table_name):
        function: str = (
            f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
        )
        session = restricted_get_session_for_saas()
        try:
            # call sts_conn with my client and pass in forced_client
            if config.get("_global_.dynamodb_server"):

                resource = session.resource(
                    "dynamodb",
                    region_name=config.region,
                    endpoint_url=config.get(
                        "_global_.dynamodb_server",
                        config.get("_global_.boto3.client_kwargs.endpoint_url"),
                    ),
                )
            else:
                resource = session.resource(
                    "dynamodb",
                    region_name=config.region,
                )
            table = resource.Table(table_name)
        except Exception as e:
            log.error({"function": function, "error": e}, exc_info=True)
            stats.count(f"{function}.exception")
            return None
        else:
            return table

    async def get_static_config_yaml_for_all_hosts(self) -> Dict[str, str]:
        """Retrieve static configuration yaml."""
        tenant_configs_l = await self.parallel_scan_table_async(
            self.tenant_static_configs,
            dynamodb_kwargs={"FilterExpression": Key("id").eq("master")},
        )
        return self.validate_and_return_tenant_configurations(tenant_configs_l)

    def validate_and_return_tenant_configurations(
        self, tenant_configs_l: List[Dict[str, Union[str, bytes]]]
    ):
        log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Validating tenant configurations",
        }
        tenant_configs = {}
        for c in tenant_configs_l:
            if not c["id"] == "master":
                # This should never  be the case, but as a safety check, let's ensure we're only loading the "master"
                # (ie latest) version of a tenant's configuration
                continue
            try:
                config_uncompressed = zlib.decompress(c["config"].value)
                config_d = yaml.safe_load(config_uncompressed)
                # TODO: Validate Pydantic Model of tenant configuration here
            except Exception as e:
                log.error(
                    {
                        **log_data,
                        "message": "Unable to parse configuration for tenant",
                        "host": c["host"],
                        "error": str(e),
                    }
                )
                sentry_sdk.capture_exception()
                continue
            tenant_configs[c["host"]] = config_d
        # TODO: Merge dynamic configuration for tenant into this model
        return tenant_configs

    def get_static_config_yaml_for_all_hosts_sync(self) -> Dict[str, str]:
        """Retrieve static configuration yaml."""
        tenant_configs_l = self.parallel_scan_table(
            self.tenant_static_configs,
            dynamodb_kwargs={"FilterExpression": Key("id").eq("master")},
        )
        return self.validate_and_return_tenant_configurations(tenant_configs_l)

    def get_static_config_for_host_sync(self, host) -> bytes:
        """Retrieve dynamic configuration yaml synchronously"""
        c = b""
        try:
            current_config = self.tenant_static_configs.get_item(
                Key={"host": host, "id": "master"}
            )
            if not current_config:
                return c
            compressed_config = current_config.get("Item", {}).get("config", "")
            if not compressed_config:
                return c
            try:
                c = zlib.decompress(compressed_config.value)
            except Exception:
                c = compressed_config.value
        except Exception as e:  # noqa

            log.error(
                {
                    "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                    "message": "Error retrieving dynamic configuration",
                    "error": str(e),
                }
            )
            sentry_sdk.capture_exception()
            c = compressed_config
        return yaml.safe_load(c)

    def get_all_hosts(self) -> List[str]:
        hosts = set()
        items = self.parallel_scan_table(
            self.tenant_static_configs,
            dynamodb_kwargs={
                "Select": "SPECIFIC_ATTRIBUTES",
                "AttributesToGet": [
                    "host",
                ],
            },
        )
        for item in items:
            hosts.add(item["host"])
        return list(hosts)

    async def update_static_config_for_host(
        self,
        new_config: str,
        updated_by: str,
        host: str,
    ) -> None:

        # TODO: We could support encrypting/decrypting static configuration automatically based on a configuration
        # passed in from AWS Secrets Manager or something else
        """Take a YAML config and writes to DDB (The reason we use YAML instead of JSON is to preserve comments)."""
        # Validate that config loads as yaml, raises exception if not
        yaml.safe_load(new_config)
        stats.count("update_dynamic_config", tags={"updated_by": updated_by})
        current_config_entry = await sync_to_async(self.tenant_static_configs.get_item)(
            Key={"host": host, "id": "master"}
        )
        current_config_entry = current_config_entry.get("Item", {})
        if current_config_entry:
            old_config = {
                "host": host,
                "id": current_config_entry["updated_at"],
                "updated_by": current_config_entry["updated_by"],
                "config": current_config_entry["config"],
                "updated_at": str(int(time.time())),
            }

            self.tenant_static_configs.put_item(
                Item=self._data_to_dynamo_replace(old_config)
            )

        new_config_writable = {
            "host": host,
            "id": "master",
            "config": new_config,
            # "config": zlib.compress(new_config.encode()),
            "updated_by": updated_by,
            "updated_at": str(int(time.time())),
        }
        self.tenant_static_configs.put_item(
            Item=self._data_to_dynamo_replace(new_config_writable)
        )


class IAMRoleDynamoHandler(BaseDynamoHandler):
    def __init__(self, host) -> None:
        try:
            self.role_table = self._get_dynamo_table(
                config.get_host_specific_key(
                    f"site_configs.{host}.aws.iamroles_dynamo_table",
                    host,
                    "consoleme_iamroles_multitenant",
                ),
                host,
            )
            self.host = host

        except Exception:
            log.error("Unable to get the IAM Role DynamoDB tables.", exc_info=True)
            raise

    @retry(
        stop_max_attempt_number=4,
        wait_exponential_multiplier=1000,
        wait_exponential_max=1000,
    )
    def _update_role_table_value(self, role_ddb: dict) -> None:
        """Run the specific DynamoDB update with retryability."""
        self.role_table.put_item(Item=role_ddb)

    @retry(
        stop_max_attempt_number=4,
        wait_exponential_multiplier=1000,
        wait_exponential_max=1000,
    )
    def fetch_iam_role(
        self,
        role_arn: str,
        host: str,
    ):
        entity_id = self.get_role_id(role_arn, host)
        return self.role_table.get_item(Key={"host": host, "entity_id": entity_id})

    def convert_iam_resource_to_json(self, role: dict) -> str:
        return json.dumps(role, default=self._json_encode_timestamps)

    def _json_encode_timestamps(self, field: datetime) -> str:
        """Solve those pesky timestamps and JSON annoyances."""
        if isinstance(field, datetime):
            return get_iso_string(field)

    def get_role_id(self, role_arn, role_host):
        return f"{role_arn}||{role_host}"

    def sync_iam_role_for_account(self, role_ddb: dict) -> None:
        """Sync the IAM roles received to DynamoDB.
        :param role_ddb:
        :return:
        """
        role_ddb["entity_id"] = self.get_role_id(role_ddb["arn"], role_ddb["host"])
        try:
            # Unfortunately, DDB does not support batch updates :(... So, we need to update each item individually :/
            self._update_role_table_value(role_ddb)

        except Exception as e:
            log_data = {
                "message": "Error syncing Account's IAM roles to DynamoDB",
                "account_id": role_ddb["accountId"],
                "role_ddb": role_ddb,
                "error": str(e),
            }
            log.error(log_data, exc_info=True)
            raise

    def fetch_all_roles(self, host):
        # TODO: Rewrite me
        response = self.role_table.query(
            KeyConditionExpression="host = :h",
            ExpressionAttributeValues={":h": host},
        )
        print(response)
        # response = self.role_table.scan()
        # items = []
        #
        # if response and "Items" in response:
        #     items = self._data_from_dynamo_replace(response["Items"])
        # while "LastEvaluatedKey" in response:
        #     response = self.role_table.scan(
        #         ExclusiveStartKey=response["LastEvaluatedKey"]
        #     )
        #     items.extend(self._data_from_dynamo_replace(response["Items"]))
        # return items


# from asgiref.sync import async_to_sync
# ddb = UserDynamoHandler("cyberdyne_noq_dev", user="ccastrapel@gmail.com")
# api_key = async_to_sync(ddb.create_api_key)("ccastrapel@gmail.com", "cyberdyne_noq_dev")
# print(api_key)
