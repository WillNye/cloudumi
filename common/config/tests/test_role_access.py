from unittest import TestCase

import pytest
from asgiref.sync import async_to_sync
from tornado.httpclient import AsyncHTTPClient

from common.config import config, role_access
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.yaml import yaml


def get_tenant_config():
    return config.get_tenant_static_config_from_dynamo("host")


def set_tenant_config(**kwargs):
    ddb = RestrictedDynamoHandler()
    tenant_config = get_tenant_config()
    tenant_config.update(kwargs)
    async_to_sync(ddb.update_static_config_for_tenant)(
        yaml.dump(dict(tenant_config)), "test", "host"  # type: ignore
    )


def delete_role_access():
    ddb = RestrictedDynamoHandler()
    tenant_config = get_tenant_config()
    if "cloud_credential_authorization_mapping" in tenant_config:
        del tenant_config["cloud_credential_authorization_mapping"]
    async_to_sync(ddb.update_static_config_for_tenant)(
        yaml.dump(dict(tenant_config)), "test", "host"  # type: ignore
    )


@pytest.mark.usefixtures("aws_credentials")
@pytest.mark.usefixtures("dynamodb")
@pytest.mark.usefixtures("with_test_configuration_tenant_static_config_data")
class TestRoleAccess(TestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestRoleAccess, self).setUp()
        self.client = AsyncHTTPClient(force_instance=True)

    def test_enable_role_access_credential_brokering(self):
        async_to_sync(role_access.toggle_role_access_credential_brokering)("host", True)
        assert (
            get_tenant_config()["cloud_credential_authorization_mapping"]["role_tags"][
                "enabled"
            ]
            is True
        )

    def test_disable_role_access_credential_brokering(self):
        async_to_sync(role_access.toggle_role_access_credential_brokering)(
            "host", False
        )
        assert (
            get_tenant_config()["cloud_credential_authorization_mapping"]["role_tags"][
                "enabled"
            ]
            is False
        )

    def test_enable_role_access_automatic_policy_update(self):
        async_to_sync(role_access.toggle_role_access_automatic_policy_update)(
            "host", True
        )
        assert (
            get_tenant_config()["aws"]["automatically_update_role_trust_policies"]
            is True
        )

    def test_disable_role_access_automatic_policy_update(self):
        async_to_sync(role_access.toggle_role_access_automatic_policy_update)(
            "host", False
        )
        assert (
            get_tenant_config()["aws"]["automatically_update_role_trust_policies"]
            is False
        )

    def test_upsert_authorized_groups_tags(self):
        async_to_sync(role_access.upsert_authorized_groups_tag)(
            "host", "test_tag", True
        )
        assert get_tenant_config()["cloud_credential_authorization_mapping"][
            "role_tags"
        ]["authorized_groups_tags"] == ["test_tag"]

    def test_delete_authorized_groups_tags(self):
        set_tenant_config(
            **{
                "cloud_credential_authorization_mapping": {
                    "role_tags": {"authorized_groups_tags": ["test_tag"]}
                }
            }
        )
        async_to_sync(role_access.delete_authorized_groups_tag)("host", "test_tag")
        assert (
            len(
                get_tenant_config()["cloud_credential_authorization_mapping"][
                    "role_tags"
                ]["authorized_groups_tags"]
            )
            == 0
        )

    def test_upsert_authorized_groups_tags_web_access(self):
        async_to_sync(role_access.upsert_authorized_groups_tag)(
            "host", "test_tag", True
        )
        assert get_tenant_config()["cloud_credential_authorization_mapping"][
            "role_tags"
        ]["authorized_groups_tags"] == ["test_tag"]

    def test_upsert_authorized_groups_tags_cli_only(self):
        async_to_sync(role_access.upsert_authorized_groups_tag)(
            "host", "test_tag", False
        )
        assert get_tenant_config()["cloud_credential_authorization_mapping"][
            "role_tags"
        ]["authorized_groups_cli_only_tags"] == ["test_tag"]
