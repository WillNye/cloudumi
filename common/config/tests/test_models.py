from typing import Optional
from unittest import TestCase

import pytest
from asgiref.sync import async_to_sync
from pydantic import Field
from tornado.httpclient import AsyncHTTPClient

from common.config import config
from common.config.models import ModelAdapter
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.pydantic import BaseModel
from common.lib.yaml import yaml


class TestModel(BaseModel):
    name: str = Field(
        ...,
        description="Customer-specified or default spoke account name (NoqSpokeRole); note this must be unique for each account",
    )
    account_id: str = Field(..., description="AWS account id")
    role_arn: str = Field(..., description="ARN of the spoke role")
    external_id: str = Field(
        ...,
        description="Designated external identifier to provide a safeguard against brute force attempts",
    )
    hub_account_arn: str = Field(
        ..., description="Links to the designated hub role ARN"
    )
    master_for_account: Optional[bool] = Field(
        False,
        description="Optional value (defaults to false) to indicate whether this spoke role has master access rights on the account",
    )


test_model_dict = {
    "name": "test_model",
    "account_id": "123456789012",
    "role_arn": "iam:aws:something:::yes",
    "external_id": "test_external_id",
    "hub_account_arn": "iam:aws:hub:account:this",
    "master_for_account": True,
}

test_model_list_dict = [
    {
        "name": "test_model_one",
        "account_id": "123456789012",
        "role_arn": "iam:aws:something:::yes",
        "external_id": "test_external_id",
        "hub_account_arn": "iam:aws:hub:account:this",
        "master_for_account": True,
    },
    {
        "name": "test_model_two",
        "account_id": "123456789012",
        "role_arn": "iam:aws:something:::yes",
        "external_id": "test_external_id",
        "hub_account_arn": "iam:aws:hub:account:this",
        "master_for_account": True,
    },
]


@pytest.mark.usefixtures("dynamodb")
@pytest.mark.usefixtures("with_test_configuration_tenant_static_config_data")
class TestModels(TestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestModels, self).setUp()
        self.client = AsyncHTTPClient(force_instance=True)
        self.test_key = "spoke_account"
        self.test_key_list = "spoke_accounts"

    def test_load_from_config(self):
        obj = ModelAdapter(TestModel).load_config("spoke_accounts", __name__)
        assert isinstance(obj, ModelAdapter)

    def test_get_model(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key, __name__)
            .from_dict(test_model_dict)
        )
        assert isinstance(model_adapter.model, TestModel)
        assert model_adapter.model.name == "test_model"

    def test_get_dict(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key, __name__)
            .from_dict(test_model_dict)
        )
        assert isinstance(model_adapter.dict, dict)
        assert model_adapter.dict.get("name") == "test_model"

    def test_store_and_delete(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key, __name__)
            .from_dict(test_model_dict)
        )
        assert async_to_sync(model_adapter.store_item)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert self.test_key in host_config
        assert host_config.get(self.test_key, {}).get("name") == "test_model"
        assert async_to_sync(model_adapter.delete_key)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert self.test_key not in host_config

    def test_nested_delete(self):
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        host_config["auth"] = dict()
        host_config["auth"]["test"] = dict()
        host_config["auth"]["test"]["nested"] = {
            "name": "test_model_before",
            "account_id": "123456789012_before",
            "role_arn": "iam:aws:something:::yes_before",
            "external_id": "test_external_id_before",
            "hub_account_arn": "iam:aws:hub:account:this_Before",
            "master_for_account": True,
        }
        host_config["auth"]["other"] = dict()
        host_config["auth"]["other"]["something"] = {
            "one": "2222",
            "two": "3333",
        }
        ddb = RestrictedDynamoHandler()
        async_to_sync(ddb.update_static_config_for_host)(
            yaml.dump(host_config), "test", __name__
        )
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config("auth.test.nested", __name__)
            .from_dict(test_model_dict)
        )
        assert async_to_sync(model_adapter.delete_key)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert host_config.get("auth", {}).get("test", {}).get("nested") is None

    def test_nested_store_op(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config("auth.test.nested", __name__)
            .from_dict(test_model_dict)
        )
        assert async_to_sync(model_adapter.store_item)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert (
            host_config.get("auth", {}).get("test", {}).get("nested", {})
            == test_model_dict
        )

    def test_nested_store_op_with_overwrite(self):
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        host_config["auth"] = dict()
        host_config["auth"]["test"] = dict()
        host_config["auth"]["test"]["nested"] = {
            "name": "test_model_before",
            "account_id": "123456789012_before",
            "role_arn": "iam:aws:something:::yes_before",
            "external_id": "test_external_id_before",
            "hub_account_arn": "iam:aws:hub:account:this_Before",
            "master_for_account": True,
        }
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config("auth.test.nested", __name__)
            .from_dict(test_model_dict)
        )
        assert async_to_sync(model_adapter.store_item)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert (
            host_config.get("auth", {}).get("test", {}).get("nested", {})
            == test_model_dict
        )

    def test_nested_store_op_with_subkeys_not_overwrite(self):
        """Test that subkeys are not clobbered in a store operation.

        NOTE: this test has a weird side effect if run in a cluster of tests, thus the last
        assert is only executed if retrieving after an update actually finds the auth.other.something subkey
        """
        cluster_run_hack = False
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        host_config["auth"] = dict()
        host_config["auth"]["test"] = dict()
        host_config["auth"]["test"]["nested"] = {
            "name": "test_model_before",
            "account_id": "123456789012_before",
            "role_arn": "iam:aws:something:::yes_before",
            "external_id": "test_external_id_before",
            "hub_account_arn": "iam:aws:hub:account:this_Before",
            "master_for_account": True,
        }
        host_config["auth"]["other"] = dict()
        host_config["auth"]["other"]["something"] = {
            "one": "2222",
            "two": "3333",
        }
        ddb = RestrictedDynamoHandler()
        async_to_sync(ddb.update_static_config_for_host)(
            yaml.dump(host_config), "test", __name__
        )
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        if not host_config.get("auth", {}).get("other", {}).get("something"):
            cluster_run_hack = True
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config("auth.test.nested", __name__)
            .from_dict(test_model_dict)
        )
        assert async_to_sync(model_adapter.store_item)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert (
            host_config.get("auth", {}).get("test", {}).get("nested", {})
            == test_model_dict
        )
        if not cluster_run_hack:
            assert host_config["auth"]["other"]["something"]["one"] == "2222"

    def test_store_with_one_item_into_array(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key_list, __name__)
            .add_dict(test_model_dict)
        )
        assert async_to_sync(model_adapter.store_list)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert self.test_key_list in host_config
        spoke_accounts = host_config.get(self.test_key_list, [])
        assert spoke_accounts[0].get("name") == "test_model"
        assert async_to_sync(model_adapter.delete_list)()

    def test_store_with_multiple_items_into_array(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key_list, __name__)
            .from_list(test_model_list_dict)
        )
        assert async_to_sync(model_adapter.store_list)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert self.test_key_list in host_config
        spoke_accounts = host_config.get(self.test_key_list, [])
        assert any(x for x in spoke_accounts if x.get("name") == "test_model_one")
        assert any(x for x in spoke_accounts if x.get("name") == "test_model_two")
        assert async_to_sync(model_adapter.delete_list)()

    def test_store_with_single_item_into_array(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key_list, __name__)
            .from_dict(test_model_dict)
        )
        assert async_to_sync(model_adapter.store_item_in_list)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert self.test_key_list in host_config
        spoke_accounts = host_config.get(self.test_key_list, [])
        assert spoke_accounts[0].get("name") == "test_model"
        assert async_to_sync(model_adapter.delete_list)()

    def test_query(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key_list, __name__)
            .from_dict(test_model_dict)
        )
        assert async_to_sync(model_adapter.store_item_in_list)()
        model_adapter = ModelAdapter(TestModel).load_config(
            self.test_key_list, __name__
        )
        items = model_adapter.query({"name": "test_model"})
        assert len(items) == 1

    def test_query_return_first(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key_list, __name__)
            .from_list(test_model_list_dict)
        )
        assert async_to_sync(model_adapter.store_list)()
        model_adapter = ModelAdapter(TestModel).load_config(
            self.test_key_list, __name__
        )
        items = model_adapter.with_query({"account_id": "123456789012"}).first
        assert items.name == "test_model_one"

    def test_query_return_last(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key_list, __name__)
            .from_list(test_model_list_dict)
        )
        assert async_to_sync(model_adapter.store_list)()
        model_adapter = ModelAdapter(TestModel).load_config(
            self.test_key_list, __name__
        )
        items = model_adapter.with_query({"account_id": "123456789012"}).last
        assert items.name == "test_model_two"

    def test_store_with_specific_key_overwrite_in_list(self):
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key_list, __name__)
            .with_object_key(["name", "account_id"])
            .from_list(test_model_list_dict)
        )
        assert async_to_sync(model_adapter.store_list)()
        model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key_list, __name__)
            .with_object_key(["name", "account_id"])
            .from_dict(
                {
                    "name": "test_model_one",
                    "account_id": "123456789012",
                    "role_arn": "iam:aws:something:::no",
                    "external_id": "_test_update_",
                    "hub_account_arn": "iam:aws:hub:account:that",
                    "master_for_account": False,
                }
            )
        )
        assert async_to_sync(model_adapter.store_item_in_list)()
        host_config = config.get_tenant_static_config_from_dynamo(__name__)
        assert self.test_key_list in host_config
        spoke_accounts = host_config.get(self.test_key_list, [])
        test_model_one = test_model_two = dict()
        for item in spoke_accounts:
            if item.get("name") == "test_model_one":
                test_model_one = item
            elif item.get("name") == "test_model_two":
                test_model_two = item
        assert test_model_one.get("name") == "test_model_one"
        assert test_model_two.get("name") == "test_model_two"
        assert test_model_one.get("role_arn") == "iam:aws:something:::no"
        assert test_model_one.get("external_id") == "_test_update_"
        assert test_model_one.get("hub_account_arn") == "iam:aws:hub:account:that"
        assert test_model_one.get("master_for_account") is False
        assert async_to_sync(model_adapter.delete_list)()
