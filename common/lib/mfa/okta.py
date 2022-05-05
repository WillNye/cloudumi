from asyncio import sleep as aio_sleep
from collections import defaultdict
from typing import Union

import okta.models as okta_models
from okta.client import Client as OktaClient

from common.config import config

log = config.get_logger(__name__)


SUPPORTED_OKTA_PROVIDERS = [okta_models.FactorProvider.OKTA]
SUPPORTED_OKTA_FACTORS = [okta_models.FactorType.PUSH]


async def okta_verify(
    host: str, user: str, url: str, api_token: str, **kwargs
) -> tuple[bool, Union[None, str]]:
    """Send a push notification to a user via okta"""
    # kwargs is to support things like passcode based authentication down the road
    okta_conn = OktaClient({"orgUrl": url, "token": api_token, "requestTimeout": 60})
    users, resp, err = await okta_conn.list_users({"filter": 'status eq "ACTIVE"'})
    if not err:
        for okta_user in users:
            if (
                okta_user.profile.login == user
                or okta_user.profile.email == user
                or okta_user.profile.secondEmail == user
            ):
                # Factors is a way to represent provider + authentication details
                supported_factors, resp, err = await okta_conn.list_factors(
                    okta_user.id
                )
                if err:
                    break

                factor_map = defaultdict(
                    dict
                )  # Build a map of factors to make prioritizing easy
                for factor in supported_factors:
                    if factor.status == okta_models.FactorStatus.ACTIVE:
                        factor_map[factor.factor_type][factor.provider] = factor

                if push_factors := factor_map.get(okta_models.FactorType.PUSH):
                    if factor := push_factors.get(okta_models.FactorProvider.OKTA):
                        verified_factor, resp, err = await okta_conn.verify_factor(
                            okta_user.id, factor.id, okta_models.VerifyFactorRequest()
                        )
                        if err:
                            break

                        factor_result = verified_factor.factor_result
                        if factor_result == okta_models.FactorResultType.SUCCESS:
                            return True, None

                        # Transaction id is not included in the response so grab it from the provided url
                        transaction_id = (
                            verified_factor.links.get("poll", {})
                            .get("href", "")
                            .split("/")
                        )
                        if not transaction_id:
                            err = ValueError("User authentication status not found")
                            break
                        transaction_id = transaction_id[-1]

                        while factor_result == okta_models.FactorResultType.WAITING:
                            await aio_sleep(2)
                            (
                                factor_response,
                                resp,
                                err,
                            ) = await okta_conn.get_factor_transaction_status(
                                okta_user.id, factor.id, transaction_id
                            )
                            factor_result = factor_response.factor_result

                        return (
                            bool(factor_result == okta_models.FactorResultType.SUCCESS),
                            None,
                        )

                if not err:
                    err = ValueError(
                        f"One of the following factors must be active: {', '.join(SUPPORTED_OKTA_FACTORS)} "
                        f"using one of the following providers: {', '.join(SUPPORTED_OKTA_PROVIDERS)}"
                    )
                    break

    log.warning(
        {
            "message": "Unable to authenticate user",
            "error": repr(err),
            "user": user,
            "host": host,
        }
    )

    if err and len(err.args) > 0:
        err = err.args[0]
    else:
        err = "User not found"

    return False, err
