import sys
from collections import defaultdict

from iambic.core.utils import evaluate_on_provider
from iambic.plugins.v0_1_0.aws.iam.role.models import (
    AWS_IAM_ROLE_TEMPLATE_TYPE,
    AwsIamRoleTemplate,
)

from common.aws.accounts.models import AWSAccount
from common.aws.role_access.models import AWSRoleAccess, RoleAccessTypes
from common.aws.utils import get_resource_arn
from common.config import config
from common.groups.models import Group
from common.iambic.interface import IambicConfigInterface
from common.iambic.templates.utils import get_template_str_value_for_provider_definition
from common.iambic_request.models import IambicRepo
from common.identity.models import AwsIdentityRole
from common.pg_core.utils import bulk_delete
from common.tenants.models import Tenant
from common.users.models import User

log = config.get_logger()


async def get_arn_to_role_template_mapping(
    aws_accounts: list[AWSAccount], role_template: AwsIamRoleTemplate
) -> dict[str, AwsIamRoleTemplate]:
    arn_mapping = {}
    for aws_account in aws_accounts:
        if not evaluate_on_provider(role_template, aws_account, False):
            continue
        role_arn = await get_resource_arn(aws_account, role_template)
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
    iambic_config_interface: IambicConfigInterface,
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
    role_mappings = await __help_get_role_mappings(iambic_config_interface)
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
    log_data = {"tenant": tenant.name}
    iambic_templates = await iambic_config_interface.load_templates(
        await iambic_config_interface.gather_templates(
            template_type=AWS_IAM_ROLE_TEMPLATE_TYPE
        ),
    )
    users = await __get_users(tenant)
    log_data["num_users"] = len(users)
    groups = await __get_groups(tenant)
    log_data["num_groups"] = len(groups)
    iambic_config = await iambic_config_interface.get_iambic_config()
    all_aws_identity_roles = await AwsIdentityRole.get_all(tenant)
    log_data["num_identity_roles"] = len(all_aws_identity_roles)
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
        template_aws_accounts = [
            account
            for account in iambic_config.aws.accounts
            if evaluate_on_provider(role_template, account, False)
        ]
        # A collection of all AWS accounts across all access rules
        if access_rules := role_template.access_rules:
            for access_rule in access_rules:
                effective_aws_accounts = [
                    account
                    for account in template_aws_accounts
                    if evaluate_on_provider(access_rule, account, False)
                ]
                for effective_aws_account in effective_aws_accounts:
                    role_arn = await get_resource_arn(
                        effective_aws_account, role_template
                    )
                    if identity_role := aws_identity_role_map.get(role_arn):
                        access_rule_users = []
                        if access_rule.users == "*":
                            access_rule_users = list(users.values())
                        elif access_rule.users:
                            for user_rule in access_rule.users:
                                if not user_rule:
                                    continue

                                user_rule = (
                                    get_template_str_value_for_provider_definition(
                                        user_rule, effective_aws_account
                                    )
                                )
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
                                if not group_rule:
                                    continue

                                group_rule = (
                                    get_template_str_value_for_provider_definition(
                                        group_rule, effective_aws_account
                                    )
                                )
                                if group := groups.get(group_rule):
                                    access_rule_groups.append(group)
                                else:
                                    log.warning(
                                        {
                                            "message": "Could not find matching group in CloudUmi's Database.",
                                            "group_rule": group_rule,
                                            "tenant": tenant.name,
                                        }
                                    )
                                # TODO: Creating groups based purely on access rules and not through a trusted relationship
                                # with a known identity provider is a bit dangerous. For now, we'll ignore these groups and log.
                                # Below is the code that could create the group. See
                                # https://noqglobal.slack.com/archives/C02HF22G4MU/p1687994448971969
                                # for more details.
                                # else:
                                #     group = Group(
                                #         managed_by="MANUAL",
                                #         description="Group automatically detected as part of IAMbic access rule",
                                #         name=group_rule,
                                #         email=group_rule,
                                #         tenant=tenant,
                                #     )
                                #     await group.write()
                                #     groups[group_rule] = group
                                #     access_rule_groups.append(group)

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
                            {
                                "message": "Could not find identity role",
                                "role_arn": role_arn,
                                "tenant": tenant.name,
                            }
                        )
        log_data["num_upserts"] = len(upserts)
        if upserts:
            await AWSRoleAccess.bulk_create(tenant, upserts)

    deleted_access = []
    for _, user_role_access_map in existing_user_role_access_map.items():
        deleted_access.extend(list(user_role_access_map.values()))
    for _, group_role_access_map in existing_group_role_access_map.items():
        deleted_access.extend(list(group_role_access_map.values()))

    log_data["num_deleted_access"] = len(deleted_access)
    if deleted_access:
        await bulk_delete(deleted_access)
    log.debug("sync_role_access results", **log_data)


async def sync_aws_role_access_for_tenant(tenant_name: str):
    fnc = f"{__name__}.{sys._getframe().f_code.co_name}"
    tenant = await Tenant.get_by_name_nocache(tenant_name)
    if not tenant:
        log.warning(
            {
                "function": fnc,
                "message": "Could not find tenant",
                "tenant": tenant_name,
            }
        )
        return
    iambic_repos = await IambicRepo.get_all_tenant_repos(tenant.name)
    if not iambic_repos:
        log.warning(
            {
                "function": fnc,
                "message": "No valid IAMbic repos found for tenant",
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
                "tenant": tenant_name,
            }
        )

    iambic_config_interface = IambicConfigInterface(iambic_repos[0])
    try:
        await sync_aws_accounts(tenant, iambic_config_interface)
    except Exception:
        log.exception(
            {
                "function": fnc,
                "message": "Error syncing aws accounts for tenant.",
                "tenant": tenant_name,
            }
        )
    try:
        await sync_identity_roles(tenant, iambic_config_interface)
    except Exception:
        log.exception(
            {
                "function": fnc,
                "message": "Error synching identity roles for tenant.",
                "tenant": tenant_name,
            }
        )
    try:
        await sync_role_access(tenant, iambic_config_interface)
    except Exception:
        log.exception(
            {
                "function": fnc,
                "message": "Error synching role access for tenant.",
                "tenant": tenant_name,
            }
        )
