import asyncio
from iambic.aws.models import AWSAccount, AWSOrganization
from iambic.config.models import AWSConfig, Config
from iambic.core.parser import load_templates
from iambic.core.utils import gather_templates


async def get_account_data(template_type: str):
    role_templates = load_templates(await gather_templates(template_type))
    configs = load_templates(await gather_templates("CORE::CONFIG"))

    for config_path in configs:
        config = Config.noq_load(config_path)
        # Need to populate AWSOrganization in iambic before calling setup_aws_accounts
        await config.setup_aws_accounts()
        for aws_account in config.aws_accounts:
            for template in role_templates:
                role_access = template.get_attribute_val_for_account(
                    aws_account, "role_access", as_boto_dict=False
                )
                role_access
                # for user in role_access.users:
                #     ...
                # for group in role_access.groups:
                #     ...

                # expires_at = (
                #     role_access.expires_at
                # )  # Write this to postgres to know if is breakglass
                # Write the aws account plus role access somewhere?

loop = asyncio.get_event_loop()
loop.run_until_complete(get_account_data("ROLE"))
