from typing import Optional
from unittest import TestCase

import pytest
from pydantic import Field
from tornado.httpclient import AsyncHTTPClient

from common.config import config
from common.config.models import ModelAdapter
from common.lib.pydantic import BaseModel


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
    "account_id": "123456789",
    "role_arn": "iam:aws:something:::yes",
    "external_id": "test_external_id",
    "hub_account_arn": "iam:aws:hub:account:this",
    "master_for_account": True,
}


class TestModels(TestCase):
    """Docstring in public class."""

    def setUp(self):
        super(TestModels, self).setUp()
        self.client = AsyncHTTPClient(force_instance=True)
        self.test_key = "spoke_accounts"
        self.test_host = "test_host"
        self.model_adapter = (
            ModelAdapter(TestModel)
            .load_config(self.test_key, self.test_host)
            .from_dict(test_model_dict)
        )

    @pytest.mark.usefixtures("with_test_configuration_tenant_static_config_data")
    def test_load_from_config(self):
        obj = ModelAdapter(TestModel).load_config("spoke_accounts", self.test_host)
        assert isinstance(obj, ModelAdapter)

    @pytest.mark.usefixtures("with_test_configuration_tenant_static_config_data")
    def test_get_model(self):
        assert isinstance(self.model_adapter.model, TestModel)
        assert self.model_adapter.model.name == "test_model"

    @pytest.mark.usefixtures("with_test_configuration_tenant_static_config_data")
    def test_get_dict(self):
        assert isinstance(self.model_adapter.dict, dict)
        assert self.model_adapter.dict.get("name") == "test_model"

    @pytest.mark.usefixtures("with_test_configuration_tenant_static_config_data")
    def test_store_and_delete(self):
        assert self.model_adapter.store()
        host_config = config.get_tenant_static_config_from_dynamo(self.test_host)
        assert self.test_key in host_config
        assert host_config.get(self.test_key, {}).get("name") == "test_model"
        assert self.model_adapter.delete()
        host_config = config.get_tenant_static_config_from_dynamo(self.test_host)
        assert self.test_key not in host_config
