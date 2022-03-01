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
