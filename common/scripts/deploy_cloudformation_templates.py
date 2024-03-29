import asyncio
import os

import boto3
import click
from jinja2 import FileSystemLoader, select_autoescape
from jinja2.sandbox import ImmutableSandboxedEnvironment


async def generate_cf_templates(upload: bool = True, suffix: str = ""):
    from common.aws.cloud_formations.utils import (
        CF_ACCOUNT_TYPES,
        get_cf_aws_cli_cmd,
        get_cf_parameters,
        get_cf_tf_body,
        get_permissions,
    )
    from common.lib.yaml import yaml
    from common.templates import TEMPLATE_DIR

    destination_dir = os.path.dirname(__file__).replace("common/scripts", "deploy")

    suffix = suffix if not suffix or suffix.startswith("_") else f"_{suffix}"
    env = ImmutableSandboxedEnvironment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        extensions=["jinja2.ext.loopcontrols"],
        autoescape=select_autoescape(),
    )
    if upload:
        boto_session = boto3.Session(profile_name="staging/staging_admin")
        s3_client = boto_session.client("s3")
    else:
        s3_client = None

    for account_type in CF_ACCOUNT_TYPES:
        cf_template = env.get_template(f"cloudumi_{account_type}_role.yaml.j2")
        permissions = await get_permissions()

        # To play nice with the CloudFormation formatting
        initial_action = permissions["read"].pop(0)
        del permissions["write"][0]
        parameters = yaml.dump(await get_cf_parameters(account_type))
        lines = parameters.splitlines()
        parameters = "\n  ".join(lines)

        cf_template_str = cf_template.render(
            initial_action=initial_action,
            read_only_actions=permissions["read"],
            read_write_actions=permissions["write"],
            parameters=parameters,
        )

        file_name = f"cloudumi_{account_type}_role{suffix}.yaml"
        file_path = os.path.join(destination_dir, file_name)
        with open(file_path, "w") as f:
            f.write(cf_template_str)

        if upload:
            s3_client.upload_file(file_path, "cloudumi-cf-templates", file_name)

        print(await get_cf_tf_body("localhost", account_type))
        print(await get_cf_aws_cli_cmd("localhost", account_type))


@click.command()
@click.option(
    "--upload",
    is_flag=True,
    show_default=True,
    help="Upload templates to S3",
)
@click.option(
    "--suffix",
    default="",
    help="Optional suffix to add to the template names. Useful for testing.",
)
def run(upload: bool, suffix: str):
    os.environ.setdefault(
        "CONFIG_LOCATION", "configs/development_account/saas_development.yaml"
    )
    os.environ.setdefault("AWS_PROFILE", "development/NoqSaasRoleLocalDev")
    asyncio.run(generate_cf_templates(upload, suffix))


if __name__ == "__main__":
    """
    Generate templates with test suffix
    python -m common.scripts.deploy_cloudformation_templates --suffix test

    Generate and upload templates with test suffix
    python -m common.scripts.deploy_cloudformation_templates --upload --suffix test

    Generate and upload templates
    python -m common.scripts.deploy_cloudformation_templates --upload
    """
    run()
