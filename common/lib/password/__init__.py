import asyncio
import random
import string
from typing import Dict, List, Optional, Union

from password_strength import PasswordPolicy

from common.config import config
from common.lib.redis import RedisHandler


async def generate_random_password(uchars=3, lchars=3, dchars=2, schars=2):
    # Generates a 10 characters long random string
    # with 3 upper case, 3 lower case, 2 digits and 2 special characters

    str_uchars, str_lchars, str_dchars, str_schars = "", "", "", ""

    for i in range(uchars):
        str_uchars += random.SystemRandom().choice(string.ascii_uppercase)

    for i in range(lchars):
        str_uchars += random.SystemRandom().choice(string.ascii_lowercase)

    for i in range(dchars):
        str_uchars += random.SystemRandom().choice(string.digits)

    for i in range(schars):
        str_uchars += random.SystemRandom().choice(string.punctuation)

    random_str = str_uchars + str_lchars + str_dchars + str_schars
    random_str = "".join(random.sample(random_str, len(random_str)))
    return random_str


async def wait_after_authentication_failure(user, tenant) -> str:
    redix_key_expiration = 60
    redis_key = f"{tenant}_wait_after_authentication_failure_{user}"
    red = RedisHandler().redis_sync(tenant)
    num_password_failures = red.get(redis_key)
    if not num_password_failures:
        num_password_failures = 0
    num_password_failures = int(num_password_failures)  # Redis values are strings
    red.setex(redis_key, redix_key_expiration, num_password_failures + 1)
    await asyncio.sleep(num_password_failures**2)
    next_delay = (num_password_failures + 1) ** 2
    return (
        f"Your next authentication failure will result in a {next_delay} second wait. "
        f"This wait time will expire after {redix_key_expiration} seconds of no authentication failures."
    )


async def check_password_strength(
    password,
    tenant: str,
) -> Optional[Union[Dict[str, str], Dict[str, List[str]]]]:
    password_policy_args = {
        "strength": config.get_tenant_specific_key(
            "auth.password_policy.strength", tenant
        ),
        "entropybits": config.get_tenant_specific_key(
            "auth.password_policy.entry_bits", tenant
        ),
        "length": config.get_tenant_specific_key(
            "auth.password_policy.length", tenant, 8
        ),
        "uppercase": config.get_tenant_specific_key(
            "auth.password_policy.uppercase", tenant, 1
        ),
        "numbers": config.get_tenant_specific_key(
            "auth.password_policy.numbers", tenant, 1
        ),
        "special": config.get_tenant_specific_key(
            "auth.password_policy.special", tenant, 1
        ),
        "nonletters": config.get_tenant_specific_key(
            "auth.password_policy.nonletters", tenant, 1
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
        return {
            "message": "Password doesn't have enough entropy. Try making it stronger",
            "errors": errors,
            "requirements": password_policy_args,
        }
