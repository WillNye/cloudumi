import asyncio
from typing import List

from common.config.models import ModelAdapter
from common.models import HubAccount, OrgAccount, SpokeAccount
from iambic.aws.models import AWSAccount, AWSOrganization, BaseAWSOrgRule
from iambic.config.models import AWSConfig, Config
from iambic.core.parser import load_templates
from iambic.core.utils import gather_templates


async def get_aws_assume_account(tenant: str) -> HubAccount:
    return ModelAdapter(HubAccount).load_config("hub_account", tenant).model


async def get_aws_accounts(tenant: str) -> List[SpokeAccount]:
    return ModelAdapter(SpokeAccount).load_config("spoke_accounts", tenant).models


async def get_aws_orgs(tenant: str) -> List[OrgAccount]:
    return ModelAdapter(OrgAccount).load_config("org_accounts", tenant).models
    

async def convert_aws_accounts_to_iambic(aws_accounts: List[SpokeAccount], aws_assume_account: HubAccount) -> List[AWSAccount]:
    return [
        AWSAccount(
            account_id=x.account_id,
            account_name=x.account_name,
            assume_role_arn=aws_assume_account.id # need arn
        ) for x in aws_accounts
    ]


async def convert_aws_orgs_to_iambic(aws_orgs: List[OrgAccount]) -> List[AWSOrganization]:
    base_rule = BaseAWSOrgRule()
    return [
        AWSOrganization(
            org_id=x.org_id,
            org_name=x.owner,
            default_rule=base_rule,
        ) for x in aws_orgs
    ]


async def get_account_data(tenant: str, template_type: str):
    role_templates = load_templates(await gather_templates(template_type))
    configs = load_templates(await gather_templates("CORE::CONFIG"))
    aws_accounts = await get_aws_accounts(tenant)
    orgs = await get_aws_orgs(tenant)
    iambic_accounts = await convert_aws_accounts_to_iambic(aws_accounts)
    iambic_orgs = await convert_aws_orgs_to_iambic(orgs)
    aws_config = AWSConfig(
        organizations=iambic_orgs,
        accounts=iambic_accounts,
    )

    for config_path in configs:
        config = Config.noq_load(aws_config, config_path)
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
loop.run_until_complete(get_account_data("localhost", "ROLE"))
