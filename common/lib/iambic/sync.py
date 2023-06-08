import asyncio
import re
from typing import Dict, List, Optional

from iambic.config.dynamic_config import Config
from iambic.config.dynamic_config import load_config as load_config_template
from iambic.config.utils import resolve_config_template_path
from iambic.core.models import BaseTemplate
from iambic.plugins.v0_1_0.aws.iam.role.models import AwsIamRoleTemplate

from common.aws.accounts.models import AWSAccount
from common.aws.role_access.models import AWSRoleAccess, RoleAccessTypes
from common.config import config
from common.config.models import ModelAdapter
from common.groups.models import Group
from common.iambic_request.models import IambicRepo
from common.identity.models import AwsIdentityRole
from common.lib.iambic.git import IambicGit
from common.lib.iambic.util import effective_accounts
from common.models import IambicRepoDetails
from common.tenants.models import Tenant
from common.users.models import User

log = config.get_logger()


async def get_data_for_template_type(
    tenant: str, template_type: str
) -> List[BaseTemplate]:
    iambic_git = IambicGit(tenant)
    access_token = await iambic_git.get_access_token()
    iambic_repo_configs = (
        ModelAdapter(IambicRepoDetails).load_config("iambic_repos", tenant).list
    )

    if not iambic_repo_configs:
        return []

    iambic_repo_config = IambicRepoDetails.parse_obj(iambic_repo_configs[0])

    repo_name = iambic_repo_config.repo_name
    iambic_repo = IambicRepo(
        tenant=tenant,
        repo_name=repo_name,
        repo_uri=f"https://oauth:{access_token}@github.com/{iambic_repo_config.repo_name}",
    )
    await iambic_repo.set_repo()
    return iambic_git.load_templates(
        await iambic_git.gather_templates(repo_name, template_type=template_type)
    )


async def get_config_data_for_repo(tenant: Tenant):
    iambic_git = IambicGit(tenant)
    access_token = await iambic_git.get_access_token()
    iambic_repo_config = None
    iambic_repo_configs = (
        ModelAdapter(IambicRepoDetails)
        .load_config("iambic_repos", str(tenant.name))
        .models
    )
    if iambic_repo_configs:
        iambic_repo_config = iambic_repo_configs[0]
    if not iambic_repo_config:
        return None
    iambic_repo = IambicRepo(
        tenant=tenant.name,
        repo_name=iambic_repo_config.repo_name,
        repo_uri=f"https://oauth:{access_token}@github.com/{iambic_repo_config.repo_name}",
    )
    # Todo: This fails the entire celery task, if it fails for just one tenant.

    config_template_path = await resolve_config_template_path(iambic_repo.file_path)
    return await load_config_template(
        config_template_path,
        configure_plugins=False,
        approved_plugins_only=True,
    )


def get_role_arn(account_id: str, role_name: str) -> str:
    return f"arn:aws:iam::{account_id}:role/{role_name}"


def get_aws_account_from_template(
    aws_accounts: AWSAccount, account_name
) -> Optional[AWSAccount]:
    aws_account = [
        x
        for x in aws_accounts
        if re.search(re.escape(account_name), x.name) or x.name == "*"
    ]

    if len(aws_account) == 0:
        # TODO: how should this be handled?
        log.warning(
            f"No corresponding account id known for Iambic included_account {account_name}"
        )
        return None
    return aws_account[0]


async def get_arn_to_role_template_mapping(
    aws_accounts: AWSAccount, role_template: AwsIamRoleTemplate
) -> Dict[str, AwsIamRoleTemplate]:
    arn_mapping = {}
    for included_account in role_template.included_accounts:
        aws_account = get_aws_account_from_template(aws_accounts, included_account)
        if aws_account is None:
            # TODO: how to handle?
            continue
        # TODO: This will not work for `identifier: '{{account_name}}_admin'`, or anything
        # with substitutions
        role_arn = get_role_arn(str(aws_account.account_id), role_template.identifier)
        arn_mapping[
            role_arn
        ] = role_template  # role_templates might represent multiple arns
    return arn_mapping


async def explode_role_templates_for_accounts(
    aws_accounts: AWSAccount, iambic_roles: List[AwsIamRoleTemplate]
) -> Dict[str, AwsIamRoleTemplate]:
    arn_mappings = {}
    for role in iambic_roles:
        arn_mappings.update(await get_arn_to_role_template_mapping(aws_accounts, role))
    return arn_mappings


async def __help_get_role_mappings(tenant: Tenant) -> Dict[str, AwsIamRoleTemplate]:
    template_type = "NOQ::AWS::IAM::Role"

    aws_accounts = await AWSAccount.get_by_tenant(tenant)
    iambic_template_rules = await get_data_for_template_type(
        str(tenant.name), template_type
    )
    return await explode_role_templates_for_accounts(
        aws_accounts, iambic_template_rules
    )


async def __get_users(tenant: Tenant) -> dict[str, User]:
    users = await User.get_all(tenant)
    return {x.email: x for x in users}


async def __get_groups(tenant: Tenant) -> dict[str, Group]:
    groups = await Group.get_all(tenant)
    return {x.name: x for x in groups}


async def sync_identity_roles(tenant: Tenant, config_template: Config):
    role_mappings = await __help_get_role_mappings(tenant)

    known_roles = await AwsIdentityRole.get_all(tenant)
    remove_roles = [x for x in known_roles if x.role_arn not in role_mappings.keys()]

    await AwsIdentityRole.delete_by_tenant_and_role_ids(
        tenant, [x.id for x in remove_roles]
    )
    await AwsIdentityRole.bulk_create(
        tenant,
        [
            {"role_name": role_template.identifier, "role_arn": role_arn}
            for role_arn, role_template in role_mappings.items()
        ],
    )


async def sync_role_access(tenant: Tenant, config_template: Config):
    arn_role_mappings: Dict[str, AwsIamRoleTemplate] = await __help_get_role_mappings(
        tenant
    )
    aws_accounts = await AWSAccount.get_by_tenant(tenant)
    users = await __get_users(tenant)
    groups = await __get_groups(tenant)

    for role_arn, role_template in arn_role_mappings.items():
        if access_rules := role_template.access_rules:
            upserts = []
            for access_rule in access_rules:
                effective_aws_accounts = effective_accounts(
                    access_rule, aws_accounts, config_template
                )
                for effective_aws_account in effective_aws_accounts:
                    role_arn = get_role_arn(
                        str(effective_aws_account.account_id), role_template.identifier
                    )
                    identity_role = await AwsIdentityRole.get_by_role_arn(
                        tenant, role_arn
                    )
                    if identity_role:
                        access_rule_users = (
                            users if access_rule.users == "*" else access_rule.users
                        )
                        for user_email in access_rule_users:
                            upserts.append(
                                {
                                    "tenant": tenant,
                                    "type": RoleAccessTypes.credential_access,
                                    "identity_role": identity_role,
                                    "cli_only": False,
                                    "expiration": access_rule.expires_at,
                                    "user": users.get(user_email),
                                }
                            )
                        access_rule_groups = (
                            groups if access_rule.groups == "*" else access_rule.groups
                        )
                        for group_name in access_rule_groups:
                            upserts.append(
                                {
                                    "tenant": tenant,
                                    "type": RoleAccessTypes.credential_access,
                                    "identity_role": identity_role,
                                    "cli_only": False,
                                    "expiration": access_rule.expires_at,
                                    "group": groups.get(group_name),
                                }
                            )
                    else:
                        log.warning(
                            f"Could not find identity role for arn {role_arn} in tenant {tenant.name}"
                        )
            await AWSRoleAccess.bulk_create(tenant, upserts)


async def sync_all_iambic_data():
    async def _sync_all_iambic_data(tenant: Tenant):
        iambic_git = IambicGit(tenant.name)
        if not iambic_git.db_tenant:
            iambic_git.db_tenant = tenant
        try:
            await iambic_git.clone_or_pull_git_repos()
            await iambic_git.sync_aws_accounts()
            await iambic_git.sync_identity_roles()
        except Exception as e:
            log.error(
                f"Error syncing iambic data for tenant {tenant.name}: {e}",
                exc_info=True,
            )
            # TODO: Most likely they don't have Git app installed

    tenants = await Tenant.get_all()
    # TODO: Remove filter
    await asyncio.gather(
        *[_sync_all_iambic_data(t) for t in tenants if t.name == "curtis_example_com"]
    )
