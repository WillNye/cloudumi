import sys

from botocore.exceptions import ClientError

import common.lib.noq_json as json
from common.config import config
from common.lib.asyncio import aio_wrapper
from common.lib.aws.session import get_session_for_tenant
from common.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "fluent_bit"))()
log = config.get_logger()


async def duo_mfa_user(username, tenant, message="Noq Authorization Request"):
    """Send a DUO mfa push request to user."""
    # Create session for the region deployed in.
    session = get_session_for_tenant(tenant)

    # Create lambda client
    client = session.client("lambda")

    # Generate the payload for the event passed to the lambda function
    payload = {"username": username, "message_type": message}

    lambda_arn = config.get_tenant_specific_key("duo.lambda_arn", tenant, None)

    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}"}

    if lambda_arn:
        try:
            # Invoke the Lambda Function that will send a DUO Push to the user
            response = await aio_wrapper(
                client.invoke,
                FunctionName=lambda_arn.format(config.region),
                InvocationType="RequestResponse",
                Payload=bytes(json.dumps(payload), "utf-8"),
            )

            stats.count(
                "duo.mfa_request",
                tags={
                    "user": username,
                    "tenant": tenant,
                },
            )
        except ClientError as e:
            log_data["error"] = e.response.get("Error", {}).get(
                "Message", "Unknown error in Duo Lambda invoke"
            )
            log.error(log_data, exc_info=True)
            # We had an error so we should deny this request
            return False

        log_data["message"] = "Duo MFA request sent to {}".format(username)

        log.info(log_data)

        # Decode and return the result
        return await decode_duo_response_from_lambda(response, username)


async def decode_duo_response_from_lambda(response, username):
    """Decode the response from the Duo lambda."""
    result = json.loads(response["Payload"].read().decode("utf-8"))
    if not result:
        return False
    if result.get("duo_auth", "") == "success":
        stats.count(
            "duo.mfa_request.approve",
            tags={
                "user": username,
            },
        )
        return True
    stats.count(
        "duo.mfa_request.deny",
        tags={
            "user": username,
        },
    )
    return False
