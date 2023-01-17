import asyncio
from typing import Dict, List

from iambic.aws.iam.role.models import RoleTemplate
from iambic.aws.models import AWSAccount
from iambic.config.utils import load_template as load_config_template
from iambic.core.parser import load_templates
from iambic.core.utils import gather_templates, yaml

from common.config import config
from common.config.models import ModelAdapter
from common.iambic_request.models import IambicRepo
from common.identity.role_access_crud import list_role_access, update_role_access
from common.models import IambicRepoConfig

log = config.get_logger()


async def get_data_for_template_type(tenant: str, template_type: str):
    iambic_repo_config = (
        ModelAdapter(IambicRepoConfig).load_config("iambic_repos", tenant).model
    )
    iambic_repo = IambicRepo(
        tenant=tenant,
        repo_name=iambic_repo_config.repo_name,
        repo_uri=f"https://oauth:{iambic_repo_config.access_token}@github.com/{iambic_repo_config.repo_name}",
    )
    await iambic_repo.set_repo()
    return load_templates(await gather_templates(iambic_repo.file_path, template_type))


async def get_config_data_for_repo(tenant: str):
    iambic_repo_config = (
        ModelAdapter(IambicRepoConfig).load_config("iambic_repos", tenant).model
    )
    iambic_repo = IambicRepo(
        tenant=tenant,
        repo_name=iambic_repo_config.repo_name,
        repo_uri=f"https://oauth:{iambic_repo_config.access_token}@github.com/{iambic_repo_config.repo_name}",
    )
    return await load_config_template(iambic_repo.file_path)


def get_role_arn(account_id: str, role_name: str) -> str:
    return f"arn:aws:iam::{account_id}:role/{role_name}"


def get_aws_account_from_template(aws_accounts: AWSAccount, account_name) -> AWSAccount:
    aws_account = [x for x in aws_accounts.accounts if x.account_name == account_name]
    if len(aws_account) == 0:
        # TODO: how should this be handled?
        log.warn(
            f"No corresponding account id known for Iambic included_account {account_name}"
        )
        return None
    return aws_account[0]


async def get_arns_for_included_accounts(
    aws_accounts: AWSAccount, role_template: [RoleTemplate]
) -> List[str]:
    arns = []
    for included_account in role_template.included_accounts:
        aws_account = get_aws_account_from_template(aws_accounts, included_account)
        if aws_account is None:
            # TODO: how to handle?
            continue
        arns.append(get_role_arn(aws_account, role_template.identifier))
    return arns


async def get_arn_to_role_template_mapping(
    aws_accounts: AWSAccount, role_template: RoleTemplate
) -> Dict[str, RoleTemplate]:
    arn_mapping = {}
    for included_account in role_template.included_accounts:
        aws_account = get_aws_account_from_template(aws_accounts, included_account)
        if aws_account is None:
            # TODO: how to handle?
            continue
        role_arn = get_role_arn(aws_account.account_id, role_template.identifier)
        arn_mapping[
            role_arn
        ] = role_template  # role_templates might represent multiple arns
    return arn_mapping


async def explode_roles_for_accounts(
    aws_accounts: AWSAccount, iambic_roles: List[RoleTemplate]
) -> List[str]:
    role_arns = []
    for role in iambic_roles:
        role_arns.extend(await get_arns_for_included_accounts(aws_accounts, role))
    return role_arns


async def explode_role_templates_for_accounts(
    aws_accounts: AWSAccount, iambic_roles: List[RoleTemplate]
) -> Dict[str, RoleTemplate]:
    arn_mappings = {}
    for role in iambic_roles:
        arn_mappings.update(await get_arn_to_role_template_mapping(aws_accounts, role))
    return arn_mappings


async def get_effective_role_access():
    pass


async def sync_role_access(tenant: str):
    template_type = "Role"

    ground_truth_roles = await get_data_for_template_type(tenant, template_type)
    config_template = await get_config_data_for_repo(tenant)

    arn_role_template_mapping = await explode_role_templates_for_accounts(
        config_template.aws, ground_truth_roles
    )

    known_roles = await list_role_access(tenant)
    create_roles = {
        k: v for k, v in arn_role_template_mapping.items() if k not in known_roles
    }
    remove_roles = {x for x in known_roles if x not in arn_role_template_mapping.keys()}
    # configs = load_templates(await gather_templates("CORE::CONFIG"))
    for config_path in configs:
        config = Config(aws=aws_config, **yaml.load(open(config_path)))
        # Need to populate AWSOrganization in iambic before calling setup_aws_accounts

        # await config.setup_aws_accounts()
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
loop.run_until_complete(sync_role_access("localhost"))
