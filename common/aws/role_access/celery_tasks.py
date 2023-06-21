import asyncio
import re
import sys
from collections import defaultdict

from iambic.core.utils import evaluate_on_provider
from iambic.plugins.v0_1_0.aws.iam.role.models import (
    AWS_IAM_ROLE_TEMPLATE_TYPE,
    AwsIamRoleTemplate,
)
from jinja2 import BaseLoader, Environment

from common.aws.accounts.models import AWSAccount
from common.aws.role_access.models import AWSRoleAccess, RoleAccessTypes
from common.config import config
from common.groups.models import Group
from common.iambic.interface import IambicConfigInterface
from common.iambic_request.models import IambicRepo
from common.identity.models import AwsIdentityRole
from common.pg_core.utils import bulk_delete
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
        arn_mapping[role_arn] = role_template
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
    iambic_config = await iambic_config_interface.get_iambic_config()
    iambic_template_rules = await iambic_config_interface.load_templates(
        await iambic_config_interface.gather_templates(
            template_type=AWS_IAM_ROLE_TEMPLATE_TYPE
        ),
    )
    return await explode_role_templates_for_accounts(
        iambic_config.aws.accounts, iambic_template_rules
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
    iambic_templates = await iambic_config_interface.load_templates(
        await iambic_config_interface.gather_templates(
            template_type=AWS_IAM_ROLE_TEMPLATE_TYPE
        ),
    )
    users = await __get_users(tenant)
    groups = await __get_groups(tenant)
    iambic_config = await iambic_config_interface.get_iambic_config()
    all_aws_identity_roles = await AwsIdentityRole.get_all(tenant)
    existing_role_access_response = await AWSRoleAccess.list(tenant)
    existing_user_role_access_map = defaultdict(dict)
    existing_group_role_access_map = defaultdict(dict)
    for role_access in existing_role_access_response:
        if role_access.user:
            existing_user_role_access_map[role_access.identity_role_id][
                role_access.user_id
            ] = role_access
        elif role_access.group:
            existing_group_role_access_map[role_access.identity_role_id][
                role_access.group_id
            ] = role_access

    aws_identity_role_map = {
        aws_identity_role.role_arn: aws_identity_role
        for aws_identity_role in all_aws_identity_roles
    }

    for role_template in iambic_templates:
        upserts = []
        if access_rules := role_template.access_rules:
            for access_rule in access_rules:
                effective_aws_accounts = [
                    account
                    for account in iambic_config.aws.accounts
                    if evaluate_on_provider(access_rule, account, False)
                ]
                for effective_aws_account in effective_aws_accounts:
                    role_arn = get_role_arn(effective_aws_account, role_template)
                    if identity_role := aws_identity_role_map.get(role_arn):
                        access_rule_users = []
                        if access_rule.users == "*":
                            access_rule_users = list(users.values())
                        elif access_rule.users:
                            for user_rule in access_rule.users:
                                if user := users.get(user_rule):
                                    access_rule_users.append(user)
                                else:
                                    log.info(
                                        {
                                            "message": "Could not find matching rule",
                                            "user_rule": user_rule,
                                            "tenant": tenant.name,
                                        }
                                    )
                        for user in access_rule_users:
                            existing_user_role_access_map[identity_role.id].pop(
                                user.id, None
                            )
                            upserts.append(
                                {
                                    "tenant": tenant,
                                    "type": RoleAccessTypes.credential_access,
                                    "identity_role": identity_role,
                                    "cli_only": False,
                                    "expiration": access_rule.expires_at,
                                    "user": user,
                                }
                            )

                        access_rule_groups = []
                        if access_rule.groups == "*":
                            access_rule_groups = list(groups.values())
                        elif access_rule.groups:
                            for group_rule in access_rule.groups:
                                if group := groups.get(group_rule):
                                    access_rule_groups.append(group)
                                else:
                                    group = Group(
                                        managed_by="MANUAL",
                                        description="Group automatically detected as part of IAMbic access rule",
                                        name=group_rule,
                                        email=group_rule,
                                        tenant=tenant,
                                    )
                                    await group.write()
                                    groups[group_rule] = group
                                    access_rule_groups.append(group)

                        for group in access_rule_groups:
                            existing_group_role_access_map[identity_role.id].pop(
                                group.id, None
                            )
                            upserts.append(
                                {
                                    "tenant": tenant,
                                    "type": RoleAccessTypes.credential_access,
                                    "identity_role": identity_role,
                                    "cli_only": False,
                                    "expiration": access_rule.expires_at,
                                    "group": group,
                                }
                            )
                    else:
                        log.warning(
                            f"Could not find identity role for arn {role_arn} in tenant {tenant.name}"
                        )

        # TODO: Remove this once we have removed all usage of the legacy noq-authorized tag
        if role_tags := [
            tag for tag in role_template.properties.tags if tag.key == "noq-authorized"
        ]:
            for role_tag in role_tags:
                effective_aws_accounts = [
                    account
                    for account in iambic_config.aws.accounts
                    if evaluate_on_provider(role_tag, account, False)
                ]
                if not effective_aws_accounts:
                    continue

                access_rule_users = []
                access_rule_groups = []
                for auth_rule in role_tag.value.split(":"):
                    if user := users.get(auth_rule):
                        access_rule_users.append(user)
                    elif group := groups.get(auth_rule):
                        access_rule_groups.append(group)
                    else:
                        log.info(
                            {
                                "message": "Could not find matching rule",
                                "auth_rule": auth_rule,
                                "tenant": tenant.name,
                            }
                        )

                for effective_aws_account in effective_aws_accounts:
                    role_arn = get_role_arn(effective_aws_account, role_template)
                    if identity_role := aws_identity_role_map.get(role_arn):
                        for user in access_rule_users:
                            existing_user_role_access_map[identity_role.id].pop(
                                user.id, None
                            )
                            upserts.append(
                                {
                                    "tenant": tenant,
                                    "type": RoleAccessTypes.credential_access,
                                    "identity_role": identity_role,
                                    "cli_only": False,
                                    "expiration": role_tag.expires_at,
                                    "user": user,
                                }
                            )
                        for group in access_rule_groups:
                            existing_group_role_access_map[identity_role.id].pop(
                                group.id, None
                            )
                            upserts.append(
                                {
                                    "tenant": tenant,
                                    "type": RoleAccessTypes.credential_access,
                                    "identity_role": identity_role,
                                    "cli_only": False,
                                    "expiration": role_tag.expires_at,
                                    "group": group,
                                }
                            )
                    else:
                        log.warning(
                            {
                                "message": "Could not find identity role",
                                "role_arn": role_arn,
                                "tenant": tenant.name,
                            }
                        )

        if upserts:
            await AWSRoleAccess.bulk_create(tenant, upserts)

    deleted_access = []
    for _, user_role_access_map in existing_user_role_access_map.items():
        deleted_access.extend(list(user_role_access_map.values()))
    for _, group_role_access_map in existing_group_role_access_map.items():
        deleted_access.extend(list(group_role_access_map.values()))

    if deleted_access:
        await bulk_delete(deleted_access)


async def sync_all_iambic_data_for_tenant(tenant_name: str):
    fnc = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenant = await Tenant.get_by_name(tenant_name)
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
        log.exception(f"Error synching identity roles for tenant {tenant.name}: {e}")
    try:
        await sync_role_access(tenant, iambic_config_interface)
    except Exception as e:
        log.exception(f"Error synching role access for tenant {tenant.name}: {e}")


async def sync_all_iambic_data():
    tenants = await Tenant.get_all()
    await asyncio.gather(
        *[sync_all_iambic_data_for_tenant(t.name) for t in tenants],
        return_exceptions=True,
    )
