from typing import Dict, List

from iambic.aws.iam.role.models import RoleTemplate
from iambic.config.utils import load_template as load_config_template
from iambic.core.models import BaseTemplate
from iambic.core.parser import load_templates
from iambic.core.utils import gather_templates

from common.aws.accounts.models import AWSAccount
from common.config import config
from common.config.models import ModelAdapter
from common.groups.models import Group
from common.iambic_request.models import IambicRepo
from common.identity.models import IdentityRole
from common.lib.iambic.util import effective_accounts
from common.models import IambicRepoConfig
from common.role_access.models import RoleAccess, RoleAccessTypes
from common.tenants.models import Tenant
from common.users.models import User

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
    aws_account = [x for x in aws_accounts if x.name == account_name]
    if len(aws_account) == 0:
        # TODO: how should this be handled?
        log.warning(
            f"No corresponding account id known for Iambic included_account {account_name}"
        )
        return None
    return aws_account[0]


async def get_arn_to_role_template_mapping(
    aws_accounts: AWSAccount, role_template: RoleTemplate
) -> Dict[str, RoleTemplate]:
    arn_mapping = {}
    for included_account in role_template.included_accounts:
        aws_account = get_aws_account_from_template(aws_accounts, included_account)
        if aws_account is None:
            # TODO: how to handle?
            continue
        role_arn = get_role_arn(aws_account.number, role_template.identifier)
        arn_mapping[
            role_arn
        ] = role_template  # role_templates might represent multiple arns
    return arn_mapping


async def explode_role_templates_for_accounts(
    aws_accounts: AWSAccount, iambic_roles: List[RoleTemplate]
) -> Dict[str, RoleTemplate]:
    arn_mappings = {}
    for role in iambic_roles:
        arn_mappings.update(await get_arn_to_role_template_mapping(aws_accounts, role))
    return arn_mappings


async def sync_aws_accounts(tenant_name: str):
    tenant = await Tenant.get_by_name(tenant_name)
    config_template = await get_config_data_for_repo(tenant.name)

    if not config_template:
        raise ValueError("Iambic config template could not be loaded")

    aws_accounts = config_template.aws.accounts
    known_accounts = await AWSAccount.get_by_tenant(tenant)
    remove_accounts = [
        x
        for x in known_accounts
        if x.name not in [x.account_name for x in aws_accounts]
    ]

    for remove_account in remove_accounts:
        await AWSAccount.delete(tenant, remove_account.number)

    for account in aws_accounts:
        await AWSAccount.create(
            tenant,
            account.account_name,
            account.account_id,
        )


async def __help_get_role_mappings(tenant_name: str) -> Dict[str, RoleTemplate]:
    template_type = "Role"

    tenant = await Tenant.get_by_name(tenant_name)
    aws_accounts = await AWSAccount.get_by_tenant(tenant)
    ground_truth_roles = await get_data_for_template_type(tenant.name, template_type)
    return await explode_role_templates_for_accounts(aws_accounts, ground_truth_roles)


async def sync_identity_roles(tenant_name: str):
    tenant = await Tenant.get_by_name(tenant_name)
    role_mappings = await __help_get_role_mappings(tenant_name)

    known_roles = await IdentityRole.get_all(tenant)
    remove_roles = [x for x in known_roles if x.role_arn not in role_mappings.keys()]

    for role_access in remove_roles:
        await IdentityRole.delete(tenant, role_access.id)

    for role_arn, role_template in role_mappings.items():
        await IdentityRole.create(tenant, role_template.identifier, role_arn)


async def sync_role_access(tenant_name: str):
    tenant = await Tenant.get_by_name(tenant_name)
    arn_role_mappings: Dict[str, RoleTemplate] = await __help_get_role_mappings(
        tenant_name
    )
    aws_accounts = await AWSAccount.get_by_tenant(tenant)

    for role_arn, role_template in arn_role_mappings.items():
        if access_rules := role_template.access_rules:
            for access_rule in access_rules:
                effective_aws_accounts = effective_accounts(access_rule, aws_accounts)
                for effective_aws_account in effective_aws_accounts:
                    role_arn = get_role_arn(
                        effective_aws_account.number, role_template.identifier
                    )
                    identity_role = await IdentityRole.get_by_role_arn(tenant, role_arn)
                    if identity_role:
                        for user_email in access_rule.users:
                            user = await User.get_by_email(tenant, user_email)
                            await RoleAccess.create(
                                tenant=tenant,
                                type=RoleAccessTypes.credential_access,
                                identity_role=identity_role,
                                cli_only=False,
                                expiration=access_rule.expiration,
                                user=user,
                            )
                        for group_name in access_rule.groups:
                            group = await Group.get_by_name(tenant, group_name)
                            await RoleAccess.create(
                                tenant=tenant,
                                type=RoleAccessTypes.credential_access,
                                identity_role=identity_role,
                                cli_only=False,
                                expiration=access_rule.expires_at,
                                group=group,
                            )
                    else:
                        log.warning(
                            f"Could not find identity role for arn {role_arn} in tenant {tenant.name}"
                        )
