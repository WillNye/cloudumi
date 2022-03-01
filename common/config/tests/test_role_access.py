from unittest.mock import patch

from asgiref.sync import async_to_sync
from tornado.httpclient import AsyncHTTPClient

from common.config import role_access
from common.lib.dynamo import RestrictedDynamoHandler
from common.tests.util import ConsoleMeAsyncHTTPTestCase


class TestRoleAccess(ConsoleMeAsyncHTTPTestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestRoleAccess, self).setUp()
        self.client = AsyncHTTPClient(force_instance=True)

    def test_enable_role_access_credential_brokering(self):
        """Docstring in public method."""
        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(
                role_access.toggle_role_access_credential_brokering("host", True)
            )
            ddb_patch.assert_called()

    def test_disable_role_access_credential_brokering(self):
        """Docstring in public method."""
        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(
                role_access.toggle_role_access_credential_brokering("host", False)
            )
            ddb_patch.assert_called()

    def test_upsert_authorized_groups_tags(self):
        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(
                role_access.upsert_authorized_groups_tag("host", "test_tag", True)
            )
            ddb_patch.assert_called()

    def test_delete_authorized_groups_tags(self):
        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(role_access.delete_authorized_groups_tag("host", "test_tag"))
            ddb_patch.assert_called()

    def test_upsert_authorized_groups_tags_web_access(self):
        with patch(
            RestrictedDynamoHandler,
            return_value={
                "cloud_credential_authorization_mapping": {
                    "authorized_groups_tags": [
                        "test_tag",
                    ]
                }
            },
        ) as ddb_patch:
            assert async_to_sync(role_access.get_authorized_groups_tag("host")) == [
                {"tag_name": "test_tag", "web_access": True}
            ]
            ddb_patch.assert_called()

    def test_upsert_authorized_groups_tags_cli_only(self):
        with patch(
            RestrictedDynamoHandler,
            return_value={
                "cloud_credential_authorization_mapping": {
                    "authorized_groups_cli_only_tags": [
                        "test_tag",
                    ]
                }
            },
        ) as ddb_patch:
            assert async_to_sync(role_access.get_authorized_groups_tag("host")) == [
                {"tag_name": "test_tag", "web_access": False}
            ]
            ddb_patch.assert_called()
