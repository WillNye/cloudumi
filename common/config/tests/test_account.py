from unittest import TestCase

import yaml
from asgiref.sync import async_to_sync
from tornado.httpclient import AsyncHTTPClient

from common.config import account, config
from common.lib.dynamo import RestrictedDynamoHandler
from common.models import HubAccount, OrgAccount, SpokeAccount


def get_hub_account():
    return HubAccount(
        name="hub_name",
        account_id="hub_account",
        role_arn="role_arn_for_hub",
        external_id="external_id_for_hub",
    )


def get_spoke_account():
    return SpokeAccount(
        name="spoke_name",
        account_id="spoke_account",
        role_arn="role_arn_for_spoke",
        external_id="extneral_id_spoke",
        hub_account_arn="hub_account_arn_for_spoke",
        master_for_account=False,
    )


def get_org_account():
    return OrgAccount(
        org_id="org_id",
        account_id="account_id_for_org",
        account_name="account_name_for_org",
        owner="owner_for_org",
    )


def get_host_config():
    return config.get_tenant_static_config_from_dynamo("host")


def set_host_config(**kwargs):
    ddb = RestrictedDynamoHandler()
    host_config = get_host_config()
    host_config.update(kwargs)
    async_to_sync(ddb.update_static_config_for_host)(
        yaml.dump(dict(host_config)), "test", "host"  # type: ignore
    )


def delete_accounts():
    ddb = RestrictedDynamoHandler()
    host_config = get_host_config()
    if "hub_account" in host_config:
        host_config.pop("hub_account")
    if "spoke_accounts" in host_config:
        host_config.pop("spoke_accounts")
    if "org_accounts" in host_config:
        host_config.pop("org_accounts")
    try:
        async_to_sync(ddb.update_static_config_for_host)(
            yaml.dump(dict(host_config)), "test", "host"  # type: ignore
        )
    except Exception:
        pass


class TestAccount(TestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestAccount, self).setUp()
        self.client = AsyncHTTPClient(force_instance=True)

    def test_set_hub_account(self):
        """Docstring in public method."""
        hub_account = get_hub_account()
        async_to_sync(account.set_hub_account)("host", hub_account)
        assert get_host_config()["hub_account"] == hub_account.dict()
        delete_accounts()

    def test_get_hub_account(self):
        hub_account = get_hub_account()
        set_host_config(hub_account=dict(hub_account))
        assert async_to_sync(account.get_hub_account)("host") == hub_account
        delete_accounts()

    def test_delete_hub_account(self):
        hub_account = get_hub_account()
        set_host_config(hub_account=hub_account.dict())
        assert async_to_sync(account.delete_hub_account)("host")
        assert "hub_account" not in get_host_config()

    def test_upsert_spoke_account(self):
        spoke_account = get_spoke_account()
        async_to_sync(account.upsert_spoke_account)("host", spoke_account)
        assert get_host_config()["spoke_accounts"] == {
            f"{spoke_account.name}__{spoke_account.account_id}": spoke_account.dict()
        }
        delete_accounts()

    def test_get_spoke_accounts(self):
        spoke_account = get_spoke_account()
        set_host_config(
            spoke_accounts={
                f"{spoke_account.name}__{spoke_account.account_id}": dict(spoke_account)
            }
        )
        assert async_to_sync(account.get_spoke_accounts)("host") == [spoke_account]
        delete_accounts()

    def test_delete_spoke_account(self):
        spoke_account = get_spoke_account()
        set_host_config(
            spoke_accounts={
                f"{spoke_account.name}__{spoke_account.account_id}": spoke_account.dict()
            }
        )
        async_to_sync(account.delete_spoke_account)(
            "host", spoke_account.name, spoke_account.account_id
        )
        assert get_host_config()["spoke_accounts"] == {}

    def test_delete_spoke_accounts(self):
        spoke_account = get_spoke_account()
        set_host_config(
            spoke_accounts={
                f"{spoke_account.name}__{spoke_account.account_id}": dict(spoke_account)
            }
        )
        async_to_sync(account.delete_spoke_accounts)("host")
        assert "spoke_accounts" not in get_host_config()

    def test_upsert_org_account(self):
        org_account = get_org_account()
        async_to_sync(account.upsert_org_account)("host", org_account)
        assert get_host_config()["org_accounts"] == {
            org_account.org_id: org_account.dict()
        }
        delete_accounts()

    def test_get_org_accounts(self):
        org_account = get_org_account()
        set_host_config(org_accounts={org_account.org_id: dict(org_account)})
        assert async_to_sync(account.get_org_accounts)("host") == [org_account]
        delete_accounts()

    def test_delete_org_account(self):
        org_account = get_org_account()
        set_host_config(org_accounts={org_account.org_id: dict(org_account)})
        assert async_to_sync(account.delete_org_account)("host", org_account.org_id)
        assert get_host_config()["org_accounts"] == {}

    def test_delete_org_accounts(self):
        org_account = get_org_account()
        set_host_config(org_accounts={org_account.org_id: dict(org_account)})
        async_to_sync(account.delete_org_accounts)("host")
        assert "org_accounts" not in get_host_config()
