from unittest.mock import patch

from asgiref.sync import async_to_sync
from tornado.httpclient import AsyncHTTPClient

from common.config import account
from common.lib.dynamo import RestrictedDynamoHandler
from common.tests.util import ConsoleMeAsyncHTTPTestCase


class TestAccount(ConsoleMeAsyncHTTPTestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestAccount, self).setUp()
        self.client = AsyncHTTPClient(force_instance=True)

    def test_set_hub_account(self):
        """Docstring in public method."""
        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(
                account.set_hub_account(
                    "host", "name", "account_id", "role_name", "external_id"
                )
            )
            ddb_patch.assert_called()

    def test_upsert_spoke_account(self):
        """Docstring in public method."""
        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(
                account.upsert_spoke_account(
                    "host",
                    "name",
                    "account_id",
                    "role_name",
                    "external_id",
                    "hub_account",
                )
            )
            ddb_patch.assert_called()

    def test_get_hub_account(self):
        with patch(
            RestrictedDynamoHandler,
            return_value={"name": "test", "account_id": "12345"},
        ) as ddb_patch:
            assert async_to_sync(account.get_hub_account("host")) == {
                "name": "test",
                "account_id": "12345",
            }
            ddb_patch.assert_called()

    def test_get_spoke_accounts(self):
        with patch(
            RestrictedDynamoHandler,
            return_value=[{"name": "test", "account_id": "12345"}],
        ) as ddb_patch:
            assert async_to_sync(account.get_spoke_accounts("host")) == [
                {"name": "test", "account_id": "12345"}
            ]
            ddb_patch.assert_called()

    def test_delete_hub_account(self):
        with patch(RestrictedDynamoHandler) as ddb_patch:
            assert async_to_sync(account.delete_hub_account("host"))
            ddb_patch.assert_called()

    def test_delete_spoke_account(self):
        with patch(RestrictedDynamoHandler) as ddb_patch:
            assert async_to_sync(
                account.delete_spoke_account("host", "name", "account_id")
            )
            ddb_patch.assert_called()

    def test_delete_spoke_accounts(self):
        with patch(RestrictedDynamoHandler) as ddb_patch:
            assert async_to_sync(account.delete_spoke_accounts("host"))
            ddb_patch.assert_called()

    def test_upsert_org_account(self):
        """Docstring in public method."""
        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(
                account.upsert_org_account(
                    "host",
                    "org_id",
                    "account_id",
                    "account_name",
                    "owner",
                )
            )
            ddb_patch.assert_called()

    def test_get_org_accounts(self):
        with patch(
            RestrictedDynamoHandler,
            return_value=[
                {
                    "org_id": "test",
                    "account_id": "12345",
                    "account_name": "name",
                    "owner": "curtis",
                }
            ],
        ) as ddb_patch:
            assert async_to_sync(account.get_org_accounts("host")) == [
                {
                    "org_id": "test",
                    "account_id": "12345",
                    "account_name": "name",
                    "owner": "curtis",
                }
            ]
            ddb_patch.assert_called()

    def test_delete_org_account(self):
        with patch(RestrictedDynamoHandler) as ddb_patch:
            assert async_to_sync(account.delete_spoke_account("host", "org_id"))
            ddb_patch.assert_called()

    def test_delete_org_accounts(self):
        with patch(RestrictedDynamoHandler) as ddb_patch:
            assert async_to_sync(account.delete_org_accounts("host"))
            ddb_patch.assert_called()
