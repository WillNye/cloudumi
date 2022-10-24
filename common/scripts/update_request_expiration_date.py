import asyncio
import os
from datetime import datetime, timezone

import click


async def update_expiration_date():
    from common.user_request.models import IAMRequest

    iam_requests: list[IAMRequest] = [
        iam_request for iam_request in await IAMRequest.scan()
    ]
    print(f"Evaluating {len(iam_requests)} requests...")
    for iam_request in iam_requests:
        if expiration_date := iam_request.extended_request.dict().get(
            "expiration_date"
        ):
            if isinstance(expiration_date, int) or len(expiration_date) == 8:
                print(f"Updating {iam_request.tenant} - {iam_request.request_id}")
                expiration_date = datetime.strptime(
                    f"{expiration_date}235959", "%Y%m%d%H%M%S"
                )
                expiration_date.replace(tzinfo=timezone.utc)
                iam_request.extended_request[
                    "expiration_date"
                ] = expiration_date.isoformat()
                await iam_request.save()


@click.command()
@click.option(
    "--environment",
    type=click.Choice(["local", "staging", "prod"]),
    help="Environment to use",
)
def run(environment):
    env_map = {
        "prod": {
            "profile": "noq_prod",
        },
        "staging": {
            "profile": "noq_staging",
        },
        "local": {
            "profile": "NoqSaasRoleLocalDev",
        },
    }

    if environment == "local":
        os.environ.setdefault(
            "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
        )

    aws_info = env_map[environment]
    os.environ.setdefault("AWS_PROFILE", aws_info["profile"])
    asyncio.run(update_expiration_date())


if __name__ == "__main__":
    """Run this directly on a container if not local

    python -m common.scripts.update_request_expiration_date --environment
    """
    run()
