import asyncio
from typing import Dict, List, Optional, Union

from password_strength import PasswordPolicy

from cloudumi_common.config import config
from cloudumi_common.lib.redis import RedisHandler


async def wait_after_authentication_failure(user, host) -> str:
    redix_key_expiration = 60
    redis_key = f"{host}_wait_after_authentication_failure_{user}"
    red = RedisHandler().redis_sync(host)
    num_password_failures = red.get(redis_key)
    if not num_password_failures:
        num_password_failures = 0
    num_password_failures = int(num_password_failures)  # Redis values are strings
    red.setex(redis_key, redix_key_expiration, num_password_failures + 1)
    await asyncio.sleep(num_password_failures ** 2)
    next_delay = (num_password_failures + 1) ** 2
    return (
        f"Your next authentication failure will result in a {next_delay} second wait. "
        f"This wait time will expire after {redix_key_expiration} seconds of no authentication failures."
    )


async def check_password_strength(
    password,
    host: str,
) -> Optional[Union[Dict[str, str], Dict[str, List[str]]]]:
    password_policy_args = {
        "strength": config.get_host_specific_key(
            f"site_configs.{host}.auth.password_policy.strength", host, 0.5
        ),
        "entropy_bits": config.get_host_specific_key(
            f"site_configs.{host}.auth.password_policy.entry_bits", host
        ),
        "length": config.get_host_specific_key(
            f"site_configs.{host}.auth.password_policy.length", host
        ),
        "uppercase": config.get_host_specific_key(
            f"site_configs.{host}.auth.password_policy.uppercase", host
        ),
        "numbers": config.get_host_specific_key(
            f"site_configs.{host}.auth.password_policy.numbers", host
        ),
        "special": config.get_host_specific_key(
            f"site_configs.{host}.auth.password_policy.special", host
        ),
        "nonletters": config.get_host_specific_key(
            f"site_configs.{host}.auth.password_policy.nonletters", host
        ),
    }

    # We remove entries with null values since password_strength doesn't like them.
    password_policy_args = {k: v for k, v in password_policy_args.items() if v}

    policy = PasswordPolicy.from_names(**password_policy_args)

    tested_pass = policy.password(password)
    errors = tested_pass.test()
    # Convert errors to string so they can be json encoded later
    errors: List[str] = [str(e) for e in errors]

    if errors:
        return {"message": "Password doesn't have enough entropy.", "errors": errors}
