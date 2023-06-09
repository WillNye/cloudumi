import asyncio
import re
from typing import Dict, List

from iambic.config.dynamic_config import Config
from iambic.config.dynamic_config import load_config as load_config_template
from iambic.config.utils import resolve_config_template_path
from iambic.core.models import BaseTemplate
from iambic.core.utils import evaluate_on_provider
from iambic.plugins.v0_1_0.aws.iam.role.models import AwsIamRoleTemplate
from jinja2.environment import Environment
from jinja2.loaders import BaseLoader

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
from common.pg_core.utils import bulk_add
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


def get_role_arn(aws_account: AWSAccount, role_template: AwsIamRoleTemplate) -> str:
    variables = {
        var.key: var.value for var in aws_account.variables
    }  # TODO: Handle this: 'arn:aws:iam::420317713496:role/Noq Audit_administrator'
    variables["account_id"] = aws_account.account_id
    variables["account_name"] = aws_account.account_name
    if hasattr(role_template, "owner") and (
        owner := getattr(role_template, "owner", None)
    ):
        variables["owner"] = owner
    role_arn = f"arn:aws:iam::{aws_account.account_id}:role{role_template.properties.path}{role_template.properties.role_name}"
    rtemplate = Environment(loader=BaseLoader()).from_string(role_arn)
    role_arn = rtemplate.render(var=variables)
    return role_arn


def get_aws_accounts_from_template(
    aws_accounts: AWSAccount, account_name
) -> list[AWSAccount]:
    aws_accounts = [
        x
        for x in aws_accounts
        if re.search(re.escape(account_name), x.name) or x.name == "*"
    ]

    if len(aws_accounts) == 0:
        # TODO: how should this be handled?
        log.warning(
            f"No corresponding account id known for Iambic included_account {account_name}"
        )
        return []
    return aws_accounts


async def get_arn_to_role_template_mapping(
    role_template: AwsIamRoleTemplate, config_template
) -> Dict[str, AwsIamRoleTemplate]:
    arn_mapping = {}
    for aws_account in config_template.aws.accounts:
        included = evaluate_on_provider(role_template, aws_account, None)
        if not included:
            continue
        role_arn = get_role_arn(aws_account, role_template)
        arn_mapping[role_arn] = role_template
    return arn_mapping


async def explode_role_templates_for_accounts(
    iambic_roles: List[AwsIamRoleTemplate],
    config_template,
) -> Dict[str, AwsIamRoleTemplate]:
    arn_mappings = {}
    for role in iambic_roles:
        arn_mappings.update(
            await get_arn_to_role_template_mapping(role, config_template)
        )
    return arn_mappings


async def __help_get_role_mappings(
    tenant: Tenant, config_template
) -> Dict[str, AwsIamRoleTemplate]:
    template_type = "NOQ::AWS::IAM::Role"

    iambic_template_rules = await get_data_for_template_type(
        str(tenant.name), template_type
    )
    return await explode_role_templates_for_accounts(
        iambic_template_rules, config_template
    )


async def __get_users(tenant: Tenant) -> dict[str, User]:
    users = await User.get_all(tenant)
    return {x.email: x for x in users}


async def __get_groups(tenant: Tenant) -> dict[str, Group]:
    groups = await Group.get_all(tenant)
    return {x.name: x for x in groups}


async def sync_identity_roles(tenant: Tenant, config_template: Config):
    role_mappings = await __help_get_role_mappings(tenant, config_template)

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
        tenant, config_template
    )
    users = await __get_users(tenant)
    groups = await __get_groups(tenant)
    upserts = []

    for role_arn, role_template in arn_role_mappings.items():
        access_rules = role_template.access_rules
        if not access_rules:
            continue
        effective_aws_accounts = []
        for access_rule in access_rules:
            effective_aws_accounts = effective_accounts(
                access_rule, config_template.aws.accounts, config_template
            )
        for effective_aws_account in effective_aws_accounts:
            role_arn = get_role_arn(effective_aws_account, role_template)
            identity_role = await AwsIdentityRole.get_by_role_arn(tenant, role_arn)
            if not identity_role:
                log.warning(
                    f"Could not find identity role for arn {role_arn} in tenant {tenant.name}"
                )
                continue
            access_rule_users = users if access_rule.users == "*" else access_rule.users
            upserts.extend(
                [
                    AWSRoleAccess(
                        tenant_id=tenant.id,
                        type=RoleAccessTypes.credential_access,
                        identity_role_id=identity_role.id,
                        cli_only=False,
                        expiration=access_rule.expires_at,
                        user_id=users.get(user_email).id,
                    )
                    for user_email in access_rule_users
                ]
            )

            access_rule_groups = (
                groups if access_rule.groups == "*" else access_rule.groups
            )

            upserts.extend(
                [
                    AWSRoleAccess(
                        tenant_id=tenant.id,
                        type=RoleAccessTypes.credential_access,
                        identity_role_id=identity_role.id,
                        cli_only=False,
                        expiration=access_rule.expires_at,
                        group_id=groups.get(group_name).id,
                    )
                    for group_name in access_rule_groups
                ]
            )
    await bulk_add(upserts)


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
