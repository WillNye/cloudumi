from unittest import TestCase
from unittest.mock import patch

from asgiref.sync import async_to_sync

from common.config import config, ip_restrictions


class TestIpRestrictions(TestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestIpRestrictions, self).setUp()

    @patch("common.lib.dynamo.RestrictedDynamoHandler")
    def test_set_ip_restriction_without_ip_restrictions(
        self, mock_restricted_dynamo_handler
    ):
        with patch.object(
            config, "get_tenant_static_config_from_dynamo", return_value={}
        ):
            assert async_to_sync(ip_restrictions.set_ip_restriction)(
                "host", "10.10.10.10/8"
            )
            assert mock_restricted_dynamo_handler.called

    @patch("common.lib.dynamo.RestrictedDynamoHandler")
    def test_set_ip_restriction_with_ip_restrictions(
        self, mock_restricted_dynamo_handler
    ):
        with patch.object(
            config,
            "get_tenant_static_config_from_dynamo",
            return_value={"ip_restrictions": []},
        ):
            assert async_to_sync(ip_restrictions.set_ip_restriction)(
                "host", "10.10.10.10/8"
            )
            assert mock_restricted_dynamo_handler.called

    @patch("common.lib.dynamo.RestrictedDynamoHandler")
    def test_delete_ip_restriction_exists(self, mock_restricted_dynamo_handler):
        with patch.object(
            config,
            "get_tenant_static_config_from_dynamo",
            return_value={"ip_restrictions": ["10.10.10.10/8"]},
        ):
            assert async_to_sync(ip_restrictions.delete_ip_restriction)(
                "host", "10.10.10.10/8"
            )
            assert mock_restricted_dynamo_handler.called

    def test_delete_ip_restriction_empty(self):
        with patch.object(
            config, "get_tenant_static_config_from_dynamo", return_value={}
        ):
            assert (
                async_to_sync(ip_restrictions.delete_ip_restriction)(
                    "host", "10.10.10.10/8"
                )
                is False
            )

    def test_delete_ip_restriction_missing(self):
        with patch.object(
            config,
            "get_tenant_static_config_from_dynamo",
            return_value={"ip_restrictions": ["1.1.1.1/32"]},
        ):
            assert (
                async_to_sync(ip_restrictions.delete_ip_restriction)(
                    "host", "10.10.10.10/8"
                )
                is False
            )

    def test_get_ip_restriction_exists(self):
        with patch.object(
            config,
            "get_host_specific_key",
            return_value={"ip_restrictions": ["10.10.10.10/10"]},
        ):
            assert async_to_sync(ip_restrictions.get_ip_restrictions)("host") == [
                "10.10.10.10/10"
            ]

    def test_get_ip_restrictions_empty(self):
        with patch.object(config, "get_host_specific_key", return_value={}):
            assert async_to_sync(ip_restrictions.get_ip_restrictions)("host") == []
