import asyncio
import re
import sys

from iambic.core.utils import evaluate_on_provider
from iambic.plugins.v0_1_0.aws.iam.role.models import (
    AWS_IAM_ROLE_TEMPLATE_TYPE,
    AwsIamRoleTemplate,
)
from jinja2 import Environment, BaseLoader

from common.aws.accounts.models import AWSAccount
from common.config import config
from common.groups.models import Group
from common.iambic.interface import IambicConfigInterface
from common.iambic_request.models import IambicRepo
from common.identity.models import AwsIdentityRole
from common.lib.iambic.util import effective_accounts
from common.aws.role_access.models import AWSRoleAccess, RoleAccessTypes
from common.tenants.models import Tenant
from common.users.models import User

log = config.get_logger()


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
    aws_accounts: list[AWSAccount], role_template: AwsIamRoleTemplate
) -> dict[str, AwsIamRoleTemplate]:
    arn_mapping = {}
    for aws_account in aws_accounts:
        if not evaluate_on_provider(role_template, aws_account, False):
            continue
        role_arn = get_role_arn(aws_account, role_template)
        arn_mapping[
            role_arn
        ] = role_template  # role_templates might represent multiple arns
    return arn_mapping


async def explode_role_templates_for_accounts(
    aws_accounts: list[AWSAccount], iambic_roles: list[AwsIamRoleTemplate]
) -> dict[str, AwsIamRoleTemplate]:
    arn_mappings = {}
    for role in iambic_roles:
        arn_mappings.update(await get_arn_to_role_template_mapping(aws_accounts, role))
    return arn_mappings


async def sync_aws_accounts(
    tenant: Tenant, iambic_config_interface: IambicConfigInterface
):
    iambic_config = await iambic_config_interface.get_iambic_config()
    aws_accounts = iambic_config.aws.accounts
    known_accounts = await AWSAccount.get_by_tenant(tenant)
    remove_accounts = [
        x
        for x in known_accounts
        if x.name not in [x.account_name for x in aws_accounts]
    ]

    await AWSAccount.delete(tenant, [x.account_id for x in remove_accounts])

    # for account in aws_accounts:
    await AWSAccount.bulk_create(
        tenant,
        [{"name": x.account_name, "account_id": x.account_id} for x in aws_accounts],
    )


async def __help_get_role_mappings(
    tenant: Tenant, iambic_config_interface: IambicConfigInterface
) -> dict[str, AwsIamRoleTemplate]:
    aws_accounts = await AWSAccount.get_by_tenant(tenant)
    iambic_template_rules = await iambic_config_interface.load_templates(
        await iambic_config_interface.gather_templates(
            template_type=AWS_IAM_ROLE_TEMPLATE_TYPE
        ),
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


async def sync_identity_roles(
    tenant: Tenant, iambic_config_interface: IambicConfigInterface
):
    role_mappings = await __help_get_role_mappings(tenant, iambic_config_interface)

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


async def sync_role_access(
    tenant: Tenant, iambic_config_interface: IambicConfigInterface
):
    arn_role_mappings: dict[str, AwsIamRoleTemplate] = await __help_get_role_mappings(
        tenant, iambic_config_interface
    )
    aws_accounts = await AWSAccount.get_by_tenant(tenant)
    users = await __get_users(tenant)
    groups = await __get_groups(tenant)
    iambic_config = await iambic_config_interface.get_iambic_config()

    for role_arn, role_template in arn_role_mappings.items():
        if access_rules := role_template.access_rules:
            upserts = []
            for access_rule in access_rules:
                effective_aws_accounts = effective_accounts(
                    access_rule, aws_accounts, iambic_config
                )
                for effective_aws_account in effective_aws_accounts:
                    role_arn = get_role_arn(
                        effective_aws_account, role_template
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
        fnc = f"{__name__}.{sys._getframe().f_code.co_name}"
        iambic_repos = await IambicRepo.get_all_tenant_repos(tenant.name)
        if not iambic_repos:
            log.warning(
                {
                    "function": fnc,
                    "message": "No Iambic Template repo has been configured.",
                    "tenant": tenant.name,
                }
            )
            return
        elif len(iambic_repos) > 1:
            log.warning(
                {
                    "function": fnc,
                    "message": "More than 1 Iambic Template repo has been configured. "
                    "This will result in data being truncated.",
                    "tenant": tenant.name,
                }
            )

        iambic_config_interface = IambicConfigInterface(iambic_repos[0])
        try:
            await sync_aws_accounts(tenant, iambic_config_interface)
        except Exception as e:
            log.exception(f"Error syncing aws accounts for tenant {tenant.name}: {e}")
        try:
            await sync_identity_roles(tenant, iambic_config_interface)
        except Exception as e:
            log.exception(
                f"Error synching identity roles for tenant {tenant.name}: {e}"
            )
        try:
            await sync_role_access(tenant, iambic_config_interface)
        except Exception as e:
            log.exception(f"Error synching role access for tenant {tenant.name}: {e}")

    tenants = await Tenant.get_all()
    await asyncio.gather(*[_sync_all_iambic_data(t) for t in tenants])
