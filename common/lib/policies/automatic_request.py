import hashlib
import json
import sys
from datetime import datetime

from common.config import config
from common.config.models import ModelAdapter
from common.lib.assume_role import boto3_cached_conn
from common.lib.asyncio import aio_wrapper
from common.lib.aws.sanitize import sanitize_session_name
from common.lib.json_encoder import SetEncoder
from common.lib.redis import RedisHandler, redis_get
from common.models import (
    AutomaticPolicyRequest,
    ExtendedAutomaticPolicyRequest,
    SpokeAccount,
    Status3,
)

log = config.get_logger(__name__)


async def create_policy(host: str, role: str, policy_document: str) -> bool:
    # TODO: If role_arn, check to see if role_arn is flagged as in_development, and if self.user is authorized for this role
    # TODO: Log all requests and actions taken during the session. eg: Google analytics for IAM
    account_id = role.split(":")[4]
    principal_name = role.split("/")[-1]
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "account_id": account_id,
        "host": host,
    }

    # TODO: Normalize the policy, make sure the identity doesn't already have the allowance, and send the request. In our case, make the change.
    spoke_role_name = (
        ModelAdapter(SpokeAccount)
        .load_config("spoke_accounts", host)
        .with_query({"account_id": account_id})
        .first.name
    )
    if not spoke_role_name:
        log_data["message"] = "Spoke role not found"
        log.warning(log_data)
        return False
    iam_client = boto3_cached_conn(
        "iam",
        host,
        account_number=account_id,
        assume_role=spoke_role_name,
        region=config.region,
        sts_client_kwargs=dict(
            region_name=config.region,
            endpoint_url=f"https://sts.{config.region}.amazonaws.com",
        ),
        client_kwargs=config.get_host_specific_key("boto3.client_kwargs", host, {}),
        session_name=sanitize_session_name("noq_automatic_policy_request_handler"),
    )
    policy_name = "generated_policy"
    # TODO: Need to ask the policy the question if it already can do what is in the permission
    # TODO: Generate formal permission request / audit trail
    # TODO: Don't overwrite existing policies
    # TODO: Generate cross-account resource policies as well, turn into a formal policy request

    try:
        await aio_wrapper(
            iam_client.put_role_policy,
            RoleName=principal_name,
            PolicyName=policy_name,
            PolicyDocument=policy_document,
        )
    except Exception as err:
        log_data["error"] = repr(err)
        log.warning(log_data)
        return False
    else:
        log_data["message"] = "Successfully created policy"
        return True


def get_policy_request_key(
    host, account_id: str = None, user: str = None, policy_request_id: str = None
) -> str:
    """Form the cache key used for automated policy requests"""
    return f"{host}_AUTOMATIC_POLICY_REQUEST_{account_id or '*'}_{user or '*'}_{policy_request_id or '*'}"


def init_extended_policy_request(**policy_request) -> ExtendedAutomaticPolicyRequest:
    policy_request["event_time"] = datetime.utcfromtimestamp(
        policy_request["event_time"]
    )
    policy_request["policy"] = json.loads(policy_request.get("policy", "[]"))
    return ExtendedAutomaticPolicyRequest(**policy_request)


async def get_policy_requests(
    host, account_id: str = None, user: str = None
) -> list[ExtendedAutomaticPolicyRequest]:
    returns = list()
    red = await RedisHandler().redis(host)
    request_keys = await aio_wrapper(
        red.keys, get_policy_request_key(host, account_id, user)
    )
    policy_requests = [
        json.loads(pol_req) for pol_req in await aio_wrapper(red.mget, request_keys)
    ]

    for policy_request in policy_requests:
        returns.append(init_extended_policy_request(**policy_request))

    return returns


async def get_policy_request(
    host, account_id: str, user: str, policy_request_id: str
) -> ExtendedAutomaticPolicyRequest:
    request_key = get_policy_request_key(host, account_id, user, policy_request_id)
    if policy_request := await redis_get(request_key, host):
        return init_extended_policy_request(**json.loads(policy_request))


async def create_policy_request(
    host: str, user: str, policy_request: AutomaticPolicyRequest
) -> ExtendedAutomaticPolicyRequest:
    red = await RedisHandler().redis(host)
    account_id = policy_request.role.split(":")[4]
    policy_dict = dict(
        host=host, account_id=account_id, user=user, **policy_request.dict()
    )
    policy_dict["policy"] = json.loads(policy_dict["policy"])

    # Generate hash to be used for id in a deterministic way
    policy_request_id = hashlib.md5(
        json.dumps(
            policy_dict, ensure_ascii=False, sort_keys=True, indent=None, cls=SetEncoder
        ).encode("utf-8")
    ).hexdigest()
    request_key = get_policy_request_key(host, account_id, user, policy_request_id)

    if extended_policy_request := await redis_get(request_key, host):
        # Gracefully handle the same policy request
        extended_policy_request = init_extended_policy_request(
            **json.loads(extended_policy_request)
        )
    else:
        account = (
            ModelAdapter(SpokeAccount)
            .load_config("spoke_accounts", host)
            .with_query({"account_id": account_id})
            .first
        )
        extended_policy_request = ExtendedAutomaticPolicyRequest(
            id=policy_request_id,
            account=account,
            host=host,
            user=user,
            role=policy_request.role,
            policy=policy_dict["policy"],
            event_time=datetime.utcnow(),
        )
        await aio_wrapper(
            red.set,
            request_key,
            json.dumps(extended_policy_request.dict(), cls=SetEncoder),
        )

    return extended_policy_request


async def update_policy_request(
    host: str, policy_request: ExtendedAutomaticPolicyRequest, cache_conn=None
) -> bool:
    if not cache_conn:
        cache_conn = await RedisHandler().redis(host)

    request_key = get_policy_request_key(
        host, policy_request.account.account_id, policy_request.user, policy_request.id
    )

    try:
        await aio_wrapper(
            cache_conn.set,
            request_key,
            json.dumps(policy_request.dict(), cls=SetEncoder),
        )
        return True
    except Exception as err:
        log.warning(
            {
                "function": f"{__name__}.{sys._getframe().f_code.co_name}",
                "policy_request_id": policy_request.id,
                "account_id": policy_request.account.account_id,
                "host": host,
                "message": "Unable to update policy request",
                "error": repr(err),
            }
        )
        return False


async def remove_policy_request(host, account_id, user, policy_request_id: str) -> bool:
    red = await RedisHandler().redis(host)
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "policy_request_id": policy_request_id,
        "account_id": account_id,
        "host": host,
    }
    try:
        red.delete(get_policy_request_key(host, account_id, user, policy_request_id))
        log_data["message"] = "Successfully removed policy"
        log.debug(log_data)
        return True
    except Exception as err:
        log_data["error"] = repr(err)
        log.warning(log_data)
        return False


async def approve_policy_request(
    host: str, account_id: str, user: str, policy_request_id: str
) -> bool:
    log_data = {
        "function": f"{__name__}.{sys._getframe().f_code.co_name}",
        "policy_request_id": policy_request_id,
        "account_id": account_id,
        "host": host,
    }
    red = await RedisHandler().redis(host)

    try:
        policy_request = await get_policy_request(
            host, account_id, user, policy_request_id
        )
        policy_request.status = Status3.approved
        await update_policy_request(host, policy_request, red)
        policy_created = await create_policy(
            host, policy_request.role, json.dumps(policy_request.policy, cls=SetEncoder)
        )
        if policy_created:
            policy_request.status = Status3.applied
            await update_policy_request(host, policy_request, red)
            log_data["message"] = "Successfully applied policy"
            log.debug(log_data)
        return policy_created

    except Exception as err:
        log_data["error"] = repr(err)
        log.warning(log_data)
        return False
