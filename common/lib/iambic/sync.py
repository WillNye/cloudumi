import asyncio
import datetime
from typing import Dict, List

from iambic.aws.iam.role.models import RoleTemplate
from iambic.aws.models import AWSAccount
from iambic.config.utils import load_template as load_config_template
from iambic.core.models import BaseTemplate
from iambic.core.parser import load_templates
from iambic.core.utils import gather_templates, yaml

from common.config import config
from common.config.models import ModelAdapter
from common.iambic_request.models import IambicRepo
from common.identity.role_access_crud import (
    create_role_access,
    get_role_access,
    list_role_access,
    update_role_access,
)
from common.models import IambicRepoConfig
from common.role_access.models import RoleAccessTypes

log = config.get_logger()


async def get_data_for_template_type(
    tenant: str, template_type: str
) -> List[BaseTemplate]:
    iambic_repo_config = (
        ModelAdapter(IambicRepoConfig).load_config("iambic_repos", tenant).model
    )
    if not iambic_repo_config:
        return []
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
    if not iambic_repo_config:
        return None
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

    if not config_template:
        return None

    arn_role_template_mapping = await explode_role_templates_for_accounts(
        config_template.aws, ground_truth_roles
    )

    known_roles = await list_role_access(tenant)
    create_roles = {
        k: v for k, v in arn_role_template_mapping.items() if k not in known_roles
    }
    update_roles = {
        k: v for k, v in arn_role_template_mapping.items() if k in known_roles
    }
    remove_roles = {x for x in known_roles if x not in arn_role_template_mapping.keys()}
    # configs = load_templates(await gather_templates("CORE::CONFIG"))

    created_by = updated_by = "iambic"

    for role_arn, role_template in create_roles.items():
        await create_role_access(
            tenant,
            created_by,
            created_at=datetime.datetime.now(),
            type=RoleAccessTypes.credential_access,  # TODO: figure out where this comes from
            user_id=None,  # TODO: need to figure out where user comes from
            group_id=None,  # TODO: need to figure out where group comes from
            identity_role=role_arn,
            cli_only=False,  # TODO: need to figure out where cli_only comes from
            expiration=role_template.expires_at,
            request_id=None,  # TODO: need to figure out where request_id comes from
            cloud_provider="aws",
        )

    for role_arn, role_template in update_roles.items():
        role = await get_role_access(tenant, role_arn)
        await update_role_access(
            tenant,
            role.id,
            updated_by,
            type=RoleAccessTypes.credential_access,  # TODO: figure out where this comes from
            user_id=None,  # TODO: need to figure out where user comes from
            group_id=None,  # TODO: need to figure out where group comes from
            identity_role=role_arn,
            cli_only=False,  # TODO: need to figure out where cli_only comes from
            expiration=role_template.expires_at,
            request_id=None,  # TODO: need to figure out where request_id comes from
            cloud_provider="aws",
        )

    for role_arn in remove_roles:
        role = await get_role_access(tenant, role_arn)
        await delete_role_access(tenant, role.id)


loop = asyncio.get_event_loop()
loop.run_until_complete(sync_role_access("localhost"))
