from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync
from tornado.httpclient import AsyncHTTPClient

from common.tests.util import ConsoleMeAsyncHTTPTestCase


@pytest.mark.usefixtures("aws_credentials")
class TestIpRestrictions(ConsoleMeAsyncHTTPTestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestIpRestrictions, self).setUp()
        self.client = AsyncHTTPClient(force_instance=True)

    def test_set_ip_restriction(self):
        from common.config import ip_restrictions
        from common.lib.dynamo import RestrictedDynamoHandler

        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(ip_restrictions.set_ip_restriction("host", "10.10.10.10/8"))
            ddb_patch.assert_called()

    def test_delete_ip_restriction(self):
        from common.config import ip_restrictions
        from common.lib.dynamo import RestrictedDynamoHandler

        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(
                ip_restrictions.delete_ip_restriction("host", "10.10.10.10/8")
            )
            ddb_patch.assert_called()

    def test_get_ip_restriction(self):
        from common.config import ip_restrictions
        from common.lib.dynamo import RestrictedDynamoHandler

        with patch(RestrictedDynamoHandler) as ddb_patch:
            async_to_sync(ip_restrictions.get_ip_restrictions("host"))
            ddb_patch.assert_called()
