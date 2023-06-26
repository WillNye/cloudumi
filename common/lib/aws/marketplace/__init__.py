import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional

import boto3
import sentry_sdk
from botocore.exceptions import ClientError
from tenacity import AsyncRetrying, RetryError, stop_after_attempt, wait_fixed
from tornado.httpclient import AsyncHTTPClient, HTTPClientError, HTTPRequest

import common.lib.noq_json as json
from common.config import config, models
from common.exceptions.exceptions import DataNotRetrievable, MissingConfigurationValue
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.messaging import iterate_event_messages
from common.lib.tenant.models import AWSMarketplaceTenantDetails
from common.models import HubAccount, SpokeAccount

log = config.get_logger()


async def return_cf_response(
    status: str,
    status_message: Optional[str],
    response_url: str,
    physical_resource_id: str,
    stack_id: str,
    request_id: str,
    logical_resource_id: str,
    tenant: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Emit an S3 error event to CloudFormation.
    """

    log_data: dict = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "status": status,
        "status_message": status_message,
        "tenant": tenant,
        "physical_resource_id": physical_resource_id,
        "message": "Responding to CloudFormation",
    }

    http_client = AsyncHTTPClient(force_instance=True)

    response_data = {
        "Status": status,
        "Reason": status_message,
        "PhysicalResourceId": physical_resource_id,
        "StackId": stack_id,
        "RequestId": request_id,
        "LogicalResourceId": logical_resource_id,
    }

    response_data_json = json.dumps(response_data)
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(response_data_json)),
    }

    http_req = HTTPRequest(
        url=response_url,
        method="PUT",
        headers=headers,
        body=json.dumps(response_data),
    )
    try:
        resp = await http_client.fetch(request=http_req)
        log_data["message"] = "Notification sent"
        log_data["response_body"] = resp.body
        log.debug(log_data)
    except (ConnectionError, HTTPClientError) as e:
        log_data["message"] = "Error occurred sending notification to CF"
        log_data["error"] = str(e)
        log.error(log_data)
        sentry_sdk.capture_exception()
        return {"statusCode": status, "body": None}

    return {"statusCode": status, "body": resp.body}


async def handle_spoke_account_registration(body):
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
    }

    spoke_role_name = body["ResourceProperties"].get("SpokeRoleName")
    account_name = body["ResourceProperties"].get("AccountName")
    account_id_for_role = body["ResourceProperties"].get("AWSAccountId")
    tenant = body["ResourceProperties"].get("Host")
    external_id = body["ResourceProperties"].get("ExternalId")
    read_only = bool(body["ResourceProperties"].get("ReadOnlyMode") == "true")

    if not spoke_role_name or not account_id_for_role or not external_id or not tenant:
        error_message = (
            "Message is missing spoke_role_name, account_id_for_role, or tenant"
        )
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "spoke_role_name": spoke_role_name,
                "account_id_for_role": account_id_for_role,
                "tenant": tenant,
                "external_id": external_id,
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    # Verify External ID
    external_id_in_config = config.get_tenant_specific_key(
        "tenant_details.external_id", tenant
    )

    retry_attempt = 1

    while not external_id_in_config and retry_attempt <= 5:
        log.error(
            {
                **log_data,
                "error": "External ID in configuration is None.",
                "retry_attempt_count": str(retry_attempt),
            }
        )
        time.sleep(5 * retry_attempt)
        external_id_in_config = config.get_tenant_specific_key(
            "tenant_details.external_id", tenant
        )
        retry_attempt += 1

    if not external_id_in_config:
        tenant_config = config.CONFIG.tenant_configs[tenant]
        tenant_config_in_redis = config.CONFIG.load_tenant_config_from_redis(tenant)
        tenant_config_in_dynamo = config.CONFIG.get_tenant_static_config_from_dynamo(
            tenant, safe=True
        )
        log.error(
            {
                **log_data,
                "tenant_config_in_memory": tenant_config,
                "tenant_config_in_redis": tenant_config_in_redis,
                "tenant_config_in_dynamo": tenant_config_in_dynamo,
            }
        )
        external_id_in_config = (
            tenant_config_in_redis.get("config", {})
            .get("tenant_details", {})
            .get("external_id")
        )
        if not external_id_in_config:
            log.error({**log_data, "message": "External ID not in loaded Redis config"})
            external_id_in_config = tenant_config_in_dynamo.get(
                "tenant_details", {}
            ).get("external_id")

        if not external_id_in_config:
            log.error(
                {
                    **log_data,
                    "message": "External ID not in loaded Dynamo config either oh no!",
                }
            )

    if external_id != external_id_in_config:
        error_message = (
            "External ID from CF doesn't match tenant's external ID configuration"
        )
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "tenant": tenant,
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    spoke_role_arn = f"arn:aws:iam::{account_id_for_role}:role/{spoke_role_name}"

    external_id = config.get_tenant_specific_key("tenant_details.external_id", tenant)
    # Get central role arn
    hub_account = (
        models.ModelAdapter(HubAccount).load_config("hub_account", tenant).model
    )
    if not hub_account:
        error_message = "No Central Role ARN detected in configuration."
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "tenant": tenant,
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    # Assume role from noq_dev_central_role
    try:
        customer_central_role_sts_client = await aio_wrapper(
            boto3_cached_conn,
            "sts",
            tenant,
            None,
            session_name="noq_test_spoke_role_registration",
        )
    except RetryError as e:
        error_message = "Unable to assume customer's central account role"
        sentry_sdk.capture_exception()
        log.error(
            {
                **log_data,
                "message": error_message,
                "cf_message": body,
                "external_id": external_id,
                "tenant": tenant,
                "error": str(e),
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3), wait=wait_fixed(3)
        ):
            with attempt:
                customer_spoke_role_credentials = await aio_wrapper(
                    customer_central_role_sts_client.assume_role,
                    RoleArn=spoke_role_arn,
                    RoleSessionName="noq_registration_verification",
                )
    except RetryError as e:
        error_message = "Unable to assume customer's spoke account role"
        sentry_sdk.capture_exception()
        log.error(
            {
                **log_data,
                "message": error_message,
                "cf_message": body,
                "external_id": external_id,
                "tenant": tenant,
                "error": str(e),
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    customer_spoke_role_iam_client = await aio_wrapper(
        boto3.client,
        "iam",
        aws_access_key_id=customer_spoke_role_credentials["Credentials"]["AccessKeyId"],
        aws_secret_access_key=customer_spoke_role_credentials["Credentials"][
            "SecretAccessKey"
        ],
        aws_session_token=customer_spoke_role_credentials["Credentials"][
            "SessionToken"
        ],
    )

    account_aliases_co = await aio_wrapper(
        customer_spoke_role_iam_client.list_account_aliases
    )
    account_aliases = account_aliases_co["AccountAliases"]
    master_account = True
    if account_aliases:
        if not account_name:
            account_name = account_aliases[0]
        master_account = False
    else:
        if not account_name:
            account_name = account_id_for_role
        # Try Organizations
        customer_spoke_role_org_client = await aio_wrapper(
            boto3.client,
            "organizations",
            aws_access_key_id=customer_spoke_role_credentials["Credentials"][
                "AccessKeyId"
            ],
            aws_secret_access_key=customer_spoke_role_credentials["Credentials"][
                "SecretAccessKey"
            ],
            aws_session_token=customer_spoke_role_credentials["Credentials"][
                "SessionToken"
            ],
        )
        try:
            account_details_call = await aio_wrapper(
                customer_spoke_role_org_client.describe_account,
                AccountId=account_id_for_role,
            )
            account_details = account_details_call.get("Account")
            if not account_name and account_details and account_details.get("Name"):
                account_name = account_details["Name"]
        except ClientError:
            # Most likely this isn't an organizations master account and we can ignore
            master_account = False

    spoke_account = SpokeAccount(
        name=spoke_role_name,
        account_name=account_name,
        account_id=account_id_for_role,
        role_arn=spoke_role_arn,
        external_id=external_id,
        hub_account_arn=hub_account.role_arn,
        org_management_account=master_account,
        read_only=read_only,
    )
    await models.ModelAdapter(
        SpokeAccount, "handle_spoke_account_registration"
    ).load_config("spoke_accounts", tenant).from_model(
        spoke_account
    ).store_item_in_list()
    return {
        "success": True,
        "message": "Successfully registered spoke account",
    }


async def handle_central_account_registration(body) -> Dict[str, Any]:
    # TODO: Fix "policies.role_name" configuration and validation
    # tenant_config["policies"]["role_name"] = spoke_role_name
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
    }

    log.info(f"ResourceProperties: {body['ResourceProperties']}")

    spoke_role_name = body["ResourceProperties"].get("SpokeRole")
    account_name = body["ResourceProperties"].get("AccountName")
    account_id_for_role = body["ResourceProperties"].get("AWSAccountId")
    role_arn = body["ResourceProperties"].get("CentralRoleArn")
    external_id = body["ResourceProperties"].get("ExternalId")
    tenant = body["ResourceProperties"].get("Host")
    read_only = bool(body["ResourceProperties"].get("ReadOnlyMode") == "true")

    if (
        not spoke_role_name
        or not account_id_for_role
        or not role_arn
        or not external_id
        or not tenant
    ):
        error_message = "Missing spoke_role_name, account_id_for_role, role_arn, external_id, or tenant in message body"
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "spoke_role_name": spoke_role_name,
                "account_id_for_role": account_id_for_role,
                "role_arn": role_arn,
                "external_id": external_id,
                "tenant": tenant,
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    external_id_in_config = config.get_tenant_specific_key(
        "tenant_details.external_id", tenant
    )

    retry_attempt = 1

    # Verify External ID
    while not external_id_in_config and retry_attempt <= 5:
        log.error(
            {
                **log_data,
                "error": "External ID in configuration is None.",
                "retry_attempt_count": str(retry_attempt),
            }
        )
        time.sleep(5 * retry_attempt)
        external_id_in_config = config.get_tenant_specific_key(
            "tenant_details.external_id", tenant
        )
        retry_attempt += 1

    if not external_id_in_config:
        tenant_config = config.CONFIG.tenant_configs[tenant]
        tenant_config_in_redis = config.CONFIG.load_tenant_config_from_redis(tenant)
        tenant_config_in_dynamo = config.CONFIG.get_tenant_static_config_from_dynamo(
            tenant, safe=True
        )
        log.error(
            {
                **log_data,
                "tenant_config_in_memory": tenant_config,
                "tenant_config_in_redis": tenant_config_in_redis,
                "tenant_config_in_dynamo": tenant_config_in_dynamo,
            }
        )
        external_id_in_config = (
            tenant_config_in_redis.get("config", {})
            .get("tenant_details", {})
            .get("external_id")
        )
        if not external_id_in_config:
            log.error({**log_data, "message": "External ID not in loaded Redis config"})
            external_id_in_config = tenant_config_in_dynamo.get(
                "tenant_details", {}
            ).get("external_id")

        if not external_id_in_config:
            log.error(
                {
                    **log_data,
                    "message": "External ID not in loaded Dynamo config either oh no!",
                }
            )

    if external_id != external_id_in_config:
        error_message = (
            "External ID from CF doesn't match tenant's external ID configuration"
        )
        sentry_sdk.capture_message(
            error_message,
            "error",
        )
        log.error(
            {
                **log_data,
                "error": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "tenant": tenant,
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    # Assume roe from noq_dev_central_role
    try:
        sts_client = boto3.client("sts")
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3), wait=wait_fixed(3)
        ):
            with attempt:
                customer_central_account_creds = await aio_wrapper(
                    sts_client.assume_role,
                    RoleArn=role_arn,
                    RoleSessionName="noq_registration_verification",
                    ExternalId=external_id,
                )
    except RetryError as e:
        error_message = "Unable to assume customer's central account role"
        sentry_sdk.capture_exception()
        log.error(
            {
                **log_data,
                "message": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "tenant": tenant,
                "error": str(e),
            }
        )
        return {
            "success": False,
            "message": error_message,
        }
    spoke_role_arn = f"arn:aws:iam::{account_id_for_role}:role/{spoke_role_name}"
    try:
        central_account_sts_client = await aio_wrapper(
            boto3.client,
            "sts",
            aws_access_key_id=customer_central_account_creds["Credentials"][
                "AccessKeyId"
            ],
            aws_secret_access_key=customer_central_account_creds["Credentials"][
                "SecretAccessKey"
            ],
            aws_session_token=customer_central_account_creds["Credentials"][
                "SessionToken"
            ],
        )
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3), wait=wait_fixed(3)
        ):
            with attempt:
                customer_spoke_role_credentials = await aio_wrapper(
                    central_account_sts_client.assume_role,
                    RoleArn=spoke_role_arn,
                    RoleSessionName="noq_registration_verification",
                )
    except RetryError as e:
        error_message = "Unable to assume customer's spoke account role"
        sentry_sdk.capture_message(error_message, "error")
        log.error(
            {
                **log_data,
                "message": error_message,
                "cf_message": body,
                "external_id_from_cf": external_id,
                "external_id_in_config": external_id_in_config,
                "tenant": tenant,
                "error": str(e),
            }
        )
        return {
            "success": False,
            "message": error_message,
        }

    if not account_name:
        customer_spoke_role_iam_client = await aio_wrapper(
            boto3.client,
            "iam",
            aws_access_key_id=customer_spoke_role_credentials["Credentials"][
                "AccessKeyId"
            ],
            aws_secret_access_key=customer_spoke_role_credentials["Credentials"][
                "SecretAccessKey"
            ],
            aws_session_token=customer_spoke_role_credentials["Credentials"][
                "SessionToken"
            ],
        )

        account_aliases_co = await aio_wrapper(
            customer_spoke_role_iam_client.list_account_aliases
        )
        account_aliases = account_aliases_co["AccountAliases"]
        if account_aliases:
            account_name = account_aliases[0]
        else:
            account_name = account_id_for_role
            # Try Organizations
            customer_spoke_role_org_client = await aio_wrapper(
                boto3.client,
                "organizations",
                aws_access_key_id=customer_spoke_role_credentials["Credentials"][
                    "AccessKeyId"
                ],
                aws_secret_access_key=customer_spoke_role_credentials["Credentials"][
                    "SecretAccessKey"
                ],
                aws_session_token=customer_spoke_role_credentials["Credentials"][
                    "SessionToken"
                ],
            )
            try:
                account_details_call = await aio_wrapper(
                    customer_spoke_role_org_client.describe_account,
                    AccountId=account_id_for_role,
                )
                account_details = account_details_call.get("Account")
                if account_details and account_details.get("Name"):
                    account_name = account_details["Name"]
            except ClientError:
                # Most likely this isn't an organizations master account and we can ignore
                pass

    hub_account = HubAccount(
        name=role_arn.split("/")[-1],
        account_name=account_name,
        account_id=account_id_for_role,
        role_arn=role_arn,
        external_id=external_id,
        read_only=read_only,
    )
    await models.ModelAdapter(HubAccount, "hub_account_onboarding").load_config(
        "hub_account", tenant
    ).from_model(hub_account).store_item()

    spoke_account = SpokeAccount(
        name=spoke_role_name,
        account_name=account_name,
        account_id=account_id_for_role,
        role_arn=spoke_role_arn,
        external_id=external_id,
        hub_account_arn=hub_account.role_arn,
        read_only=read_only,
    )
    await models.ModelAdapter(
        SpokeAccount, "handle_central_account_registration"
    ).load_config("spoke_accounts", tenant).from_model(
        spoke_account
    ).store_item_in_list()
    return {"success": True}


async def handle_aws_marketplace_queue(
    queue_arn,
    max_num_messages_to_process: Optional[int] = None,
) -> Dict[str, Any]:

    if not max_num_messages_to_process:
        max_num_messages_to_process = config.get(
            "_global_.noq_registration.max_num_messages_to_process",
            100,
        )

    queue_name = queue_arn.split(":")[-1]
    queue_region = queue_arn.split(":")[3]

    sqs_client = boto3.client("sqs", region_name=queue_region)

    queue_url_res = await aio_wrapper(sqs_client.get_queue_url, QueueName=queue_name)
    queue_url = queue_url_res.get("QueueUrl")
    if not queue_url:
        raise DataNotRetrievable(f"Unable to retrieve Queue URL for {queue_arn}")

    messages_awaitable = await aio_wrapper(
        sqs_client.receive_message, QueueUrl=queue_url, MaxNumberOfMessages=10
    )
    messages = messages_awaitable.get("Messages", [])
    num_events = 0
    while messages:
        if num_events >= max_num_messages_to_process:
            break
        processed_messages = []

        for message in iterate_event_messages(queue_region, queue_name, messages):
            num_events += 1
            try:
                message_id = message.get("message_id")
                receipt_handle = message.get("receipt_handle")
                processed_messages.append(
                    {
                        "Id": message_id,
                        "ReceiptHandle": receipt_handle,
                    }
                )
                customer_id = message["body"].get("customer_identifier")
                try:
                    customer_awsmp_data = await AWSMarketplaceTenantDetails.get(
                        customer_id
                    )
                except AWSMarketplaceTenantDetails.DoesNotExist:
                    customer_awsmp_data = None
                if not customer_awsmp_data:
                    customer_awsmp_data = await AWSMarketplaceTenantDetails.create(
                        customer_id,
                    )
                action = message["body"]["action"]
                if action == "subscribe-success":
                    customer_awsmp_data.successfully_subscribed = True
                    customer_awsmp_data.subscription_action = "subscribe-success"
                elif action == "subscribe-fail":
                    customer_awsmp_data.successfully_subscribed = False
                    customer_awsmp_data.subscription_action = "subscribe-fail"
                elif action == "unsubscribe-pending":
                    customer_awsmp_data.subscription_expired = True
                    customer_awsmp_data.subscription_action = "unsubscribe-pending"
                elif action == "unsubscribe-success":
                    customer_awsmp_data.subscription_expired = True
                    customer_awsmp_data.subscription_action = "unsubscribe-success"
                customer_awsmp_data.is_free_trial_term_present = message.get(
                    "isFreeTrialTermPresent", False
                )
                customer_awsmp_data.product_code = message.get("product-code")
                customer_awsmp_data.updated_at = int((datetime.utcnow()).timestamp())

                if customer_awsmp_data.change_history:
                    customer_awsmp_data.change_history.append(
                        {str(datetime.utcnow()): action}
                    )
                else:
                    customer_awsmp_data.change_history = [
                        {str(datetime.utcnow()): action}
                    ]

                await customer_awsmp_data.save()
                #  TODO: Need to resolve tenant_details and update tenant there if it exists
                # Update tenant tier/status
                # Limit usage based on tier
            except Exception as e:
                log.exception(
                    {
                        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                        "message": "Error processing AWS Marketplace message",
                        "aws_marketplace_message": message,
                        "error": str(e),
                    }
                )

        if processed_messages:
            await aio_wrapper(
                sqs_client.delete_message_batch,
                QueueUrl=queue_url,
                Entries=processed_messages,
            )
        messages_awaitable = await aio_wrapper(
            sqs_client.receive_message, QueueUrl=queue_url, MaxNumberOfMessages=10
        )
        messages = messages_awaitable.get("Messages", [])
    return {"message": "Successfully processed all messages", "num_events": num_events}
