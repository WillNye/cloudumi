from typing import List

from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml

updated_by_name = "noq_automated_account_management"


def __setup_subkeys_if_missing(tenant_config: dict) -> dict:
    if not tenant_config.get("cloud_credential_authorization_mapping"):
        tenant_config["cloud_credential_authorization_mapping"] = dict()
    if "role_tags" not in tenant_config["cloud_credential_authorization_mapping"]:
        tenant_config["cloud_credential_authorization_mapping"]["role_tags"] = dict()
    if (
        "authorized_groups_tags"
        not in tenant_config["cloud_credential_authorization_mapping"]["role_tags"]
    ):
        tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_tags"
        ] = list()
    if (
        "authorized_groups_cli_only_tags"
        not in tenant_config["cloud_credential_authorization_mapping"]["role_tags"]
    ):
        tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_cli_only_tags"
        ] = list()
    return tenant_config


async def upsert_authorized_groups_tag(tenant: str, tag_name: str, web_access: bool):
    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    tenant_config = __setup_subkeys_if_missing(tenant_config)

    if web_access:
        tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_tags"
        ].append(tag_name)
        if (
            tag_name
            in tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
                "authorized_groups_cli_only_tags"
            ]
        ):
            tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
                "authorized_groups_cli_only_tags"
            ].remove(tag_name)
    else:
        tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_cli_only_tags"
        ].append(tag_name)
        if (
            tag_name
            in tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
                "authorized_groups_tags"
            ]
        ):
            tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
                "authorized_groups_tags"
            ].remove(tag_name)

    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), updated_by_name, tenant  # type: ignore
    )


async def delete_authorized_groups_tag(tenant: str, tag_name: str) -> bool:
    ddb = RestrictedDynamoHandler()
    deleted = False
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    tenant_config = __setup_subkeys_if_missing(tenant_config)

    try:
        tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_tags"
        ].remove(tag_name)
        deleted = True
    except ValueError:
        pass
    try:
        tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_cli_only_tags"
        ].remove(tag_name)
        deleted = True
    except ValueError:
        pass

    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), updated_by_name, tenant  # type: ignore
    )

    return deleted


async def get_authorized_groups_tags(tenant: str) -> List[dict]:
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    groups_tags = list()
    for groups_tag in (
        tenant_config.get("cloud_credential_authorization_mapping", {})
        .get("role_tags", {})
        .get("authorized_groups_tags", [])
    ):
        # using a hard coded "source": "noq" because two kv in a list of dicts does weird things in pydantic
        groups_tags.append(
            {
                "tag_name": groups_tag,
                "web_access": True,
                "source": "noq",
            }
        )
    for groups_tag in (
        tenant_config.get("cloud_credential_authorization_mapping", {})
        .get("role_tags", {})
        .get("authorized_groups_cli_only_tags", [])
    ):
        groups_tags.append(
            {"tag_name": groups_tag, "web_access": False, "source": "noq"}
        )
    return groups_tags


async def toggle_role_access_credential_brokering(tenant: str, enabled: bool) -> bool:
    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    if "cloud_credential_authorization_mapping" not in tenant_config:
        tenant_config = __setup_subkeys_if_missing(tenant_config)
    tenant_config["cloud_credential_authorization_mapping"]["role_tags"][
        "enabled"
    ] = enabled
    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), updated_by_name, tenant  # type: ignore
    )

    if not enabled:
        await toggle_tra_access_credential_brokering(tenant, enabled)
    return True


async def toggle_tra_access_credential_brokering(tenant: str, enabled: bool) -> bool:
    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    if "cloud_credential_authorization_mapping" not in tenant_config:
        tenant_config = __setup_subkeys_if_missing(tenant_config)
    tenant_config["temporary_role_access_requests"]["enabled"] = enabled
    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), updated_by_name, tenant  # type: ignore
    )
    return True


async def get_role_access_credential_brokering(tenant: str) -> bool:
    tenant_config = config.get_tenant_specific_key(
        "cloud_credential_authorization_mapping", tenant, {}
    )
    return tenant_config.get("role_tags", {}).get("enabled", False)


async def get_tra_access_credential_brokering(tenant: str) -> bool:
    tenant_config = config.get_tenant_specific_key(
        "temporary_role_access_requests", tenant, {}
    )
    return tenant_config.get("enabled", False)


async def get_role_access_automatic_policy_update(tenant: str) -> bool:
    tenant_config = config.get_tenant_specific_key("aws", tenant, {})
    return tenant_config.get("automatically_update_role_trust_policies", False)


async def toggle_role_access_automatic_policy_update(
    tenant: str, enabled: bool
) -> bool:
    ddb = RestrictedDynamoHandler()
    tenant_config = config.get_tenant_static_config_from_dynamo(tenant)
    if "aws" not in tenant_config:
        tenant_config["aws"] = dict()
    tenant_config["aws"]["automatically_update_role_trust_policies"] = enabled
    await ddb.update_static_config_for_tenant(
        yaml.dump(tenant_config), updated_by_name, tenant  # type: ignore
    )
