from unittest import TestCase
from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync

from common.config import config, ip_restrictions


@pytest.mark.usefixtures("aws_credentials")
@pytest.mark.usefixtures("dynamodb")
@pytest.mark.usefixtures("with_test_configuration_tenant_static_config_data")
class TestIpRestrictions(TestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestIpRestrictions, self).setUp()

    def test_set_ip_restriction_without_ip_restrictions(self):
        with patch.object(
            config, "get_tenant_static_config_from_dynamo", return_value={}
        ):
            assert async_to_sync(ip_restrictions.set_ip_restriction)(
                "host", "10.10.10.10/8"
            )

    def test_set_ip_restriction_with_ip_restrictions(self):
        with patch.object(
            config,
            "get_tenant_static_config_from_dynamo",
            return_value={"ip_restrictions": []},
        ):
            assert async_to_sync(ip_restrictions.set_ip_restriction)(
                "host", "10.10.10.10/8"
            )

    def test_delete_ip_restriction_exists(self):
        assert async_to_sync(ip_restrictions.set_ip_restriction)(
            "host", "10.10.10.10/8"
        )
        assert async_to_sync(ip_restrictions.delete_ip_restriction)(
            "host", "10.10.10.10/8"
        )

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
            return_value=["10.10.10.10/10"],
        ):
            assert async_to_sync(ip_restrictions.get_ip_restrictions)("host") == [
                "10.10.10.10/10"
            ]

    def test_get_ip_restrictions_empty(self):
        with patch.object(config, "get_host_specific_key", return_value={}):
            assert async_to_sync(ip_restrictions.get_ip_restrictions)("host") == []

    def test_toggle_ip_restrictions(self):
        with patch.object(
            config,
            "get_tenant_static_config_from_dynamo",
            return_value={"policies": {"ip_restrictions": False}},
        ):
            assert async_to_sync(ip_restrictions.toggle_ip_restrictions)(
                "host", enabled=True
            )

    def test_toggle_ip_restrictions_on_requester_ip_only(self):
        with patch.object(
            config,
            "get_tenant_static_config_from_dynamo",
            return_value={"policies": {"ip_restrictions_on_requesters_ip": False}},
        ):
            assert async_to_sync(
                ip_restrictions.toggle_ip_restrictions_on_requester_ip_only
            )("host", enabled=True)
