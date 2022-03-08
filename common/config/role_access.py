from typing import List

from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml

updated_by_name = "noq_automated_account_management"


def __setup_subkeys_if_missing(host_config: dict) -> dict:
    if not host_config.get("cloud_credential_authorization_mapping"):
        host_config["cloud_credential_authorization_mapping"] = dict()
    if "role_tags" not in host_config["cloud_credential_authorization_mapping"]:
        host_config["cloud_credential_authorization_mapping"]["role_tags"] = dict()
    if (
        "authorized_groups_tags"
        not in host_config["cloud_credential_authorization_mapping"]["role_tags"]
    ):
        host_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_tags"
        ] = list()
    if (
        "authorized_groups_cli_only_tags"
        not in host_config["cloud_credential_authorization_mapping"]["role_tags"]
    ):
        host_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_cli_only_tags"
        ] = list()
    return host_config


async def upsert_authorized_groups_tag(host: str, tag_name: str, web_access: bool):
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    host_config = __setup_subkeys_if_missing(host_config)

    if web_access:
        host_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_tags"
        ].append(tag_name)
        if (
            tag_name
            in host_config["cloud_credential_authorization_mapping"]["role_tags"][
                "authorized_groups_cli_only_tags"
            ]
        ):
            host_config["cloud_credential_authorization_mapping"]["role_tags"][
                "authorized_groups_cli_only_tags"
            ].remove(tag_name)
    else:
        host_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_cli_only_tags"
        ].append(tag_name)
        if (
            tag_name
            in host_config["cloud_credential_authorization_mapping"]["role_tags"][
                "authorized_groups_tags"
            ]
        ):
            host_config["cloud_credential_authorization_mapping"]["role_tags"][
                "authorized_groups_tags"
            ].remove(tag_name)

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )


async def delete_authorized_groups_tag(host: str, tag_name: str) -> bool:
    ddb = RestrictedDynamoHandler()
    deleted = False
    host_config = config.get_tenant_static_config_from_dynamo(host)
    host_config = __setup_subkeys_if_missing(host_config)

    try:
        host_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_tags"
        ].remove(tag_name)
        deleted = True
    except ValueError:
        pass
    try:
        host_config["cloud_credential_authorization_mapping"]["role_tags"][
            "authorized_groups_cli_only_tags"
        ].remove(tag_name)
        deleted = True
    except ValueError:
        pass

    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )

    return deleted


async def get_authorized_groups_tags(host: str) -> List[dict]:
    host_config = config.get_tenant_static_config_from_dynamo(host)
    groups_tags = list()
    for groups_tag in (
        host_config.get("cloud_credential_authorization_mapping", {})
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
        host_config.get("cloud_credential_authorization_mapping", {})
        .get("role_tags", {})
        .get("authorized_groups_cli_only_tags", [])
    ):
        groups_tags.append(
            {"tag_name": groups_tag, "web_access": False, "source": "noq"}
        )
    return groups_tags


async def toggle_role_access_credential_brokering(host: str, enabled: bool) -> bool:
    ddb = RestrictedDynamoHandler()
    host_config = config.get_tenant_static_config_from_dynamo(host)
    if "cloud_credential_authorization_mapping" not in host_config:
        host_config = __setup_subkeys_if_missing(host_config)
    host_config["cloud_credential_authorization_mapping"]["role_tags"][
        "enabled"
    ] = enabled
    await ddb.update_static_config_for_host(
        yaml.dump(host_config), updated_by_name, host  # type: ignore
    )
    return True


async def get_role_access_credential_brokering(host: str) -> bool:
    host_config = config.get_host_specific_key(
        "cloud_credential_authorization_mapping", host, {}
    )
    return host_config.get("role_tags", {}).get("enabled", False)