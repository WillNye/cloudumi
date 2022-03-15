from typing import Any, Union

from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.pydantic import BaseModel
from common.lib.yaml import yaml

UPDATED_BY = "NOQ_Automaton"


class ModelAdapter:
    def __init__(self, pydantic_model_class: BaseModel, updated_by: str = UPDATED_BY):
        self._model_class = pydantic_model_class
        self._model = BaseModel()
        self._key = None
        self._host = None
        self._default = None
        self._updated_by = updated_by

    def __access_subkey(self, config_item: dict, key: str, default: Any = None) -> dict:
        parts = key.split(".")
        if len(parts) > 0:
            for k in parts[:-1]:
                config_item = config_item.get(k, {})
        config_item = config_item.get(parts[-1])
        return config_item or default

    def __access_subkey_parent(
        self, config_item: dict, key: str, default: Any = None
    ) -> dict:
        parts = key.split(".")
        if len(parts) > 1:
            for k in parts[:-1]:
                config_item = config_item.get(k, {})
        if len(parts) == 1:
            return config_item
        if len(parts) == 0:
            return default
        return config_item or default

    def __optimistic_loader(
        self, key: str, host: str = None, default: Any = None
    ) -> dict:
        if host:
            config_item = config.get_host_specific_key(key, host, default)
            if not config_item:
                config_item: dict = (
                    config.get_tenant_static_config_from_dynamo(host) or dict()
                )
                config_item = self.__access_subkey(config_item, key, default)
        else:
            config_item = config.get(key, default)
        return config_item

    def __nested_store(self, config_item: dict, key: str, value: BaseModel) -> dict:
        if not config_item:
            config_item = dict()

        segmented_key = key.split(".")
        if len(segmented_key) == 1:
            # Base Condition
            config_item[key] = dict(value)
            return config_item

        if not segmented_key[0] in config_item:
            config_item[segmented_key[0]] = dict()
        config_item[segmented_key[0]] = self.__nested_store(
            config_item[segmented_key[0]], ".".join(segmented_key[1:]), value
        )
        return config_item

    def load_config(self, key: str, host: str = None, default: Any = None) -> object:
        """Required to be run before using any other functions."""
        self._key = key
        self._host = host
        self._default = default
        config_item = self.__optimistic_loader(key, host, default)
        if config_item and not isinstance(config_item, dict):
            raise ValueError(
                f"Expect configuration object to be of type dict, got {type(config_item)} instead: {config_item}"
            )
        elif config_item:
            self._model = self._model_class.parse_obj(config_item)
        return self

    def from_dict(self, model_dict: dict) -> object:
        self._model = self._model_class.parse_obj(model_dict)
        return self

    @property
    def model(self) -> Union[BaseModel, None]:
        """Easy getter"""
        return self._model

    @property
    def dict(self) -> dict:
        """Easy getter"""
        if self._model is None:
            raise ValueError(
                "Internal model state is None; this indicates improper initialization"
            )
        return self._model.dict()

    async def store(self) -> bool:
        """Break the chain; meant as an end state function."""
        ddb = RestrictedDynamoHandler()
        host_config = config.get_tenant_static_config_from_dynamo(self._host)
        host_config = self.__nested_store(host_config, self._key, self._model)
        await ddb.update_static_config_for_host(
            yaml.dump(host_config), self._updated_by, self._host
        )
        return True

    async def delete(self, delete_root: bool = False) -> bool:
        """Break the chain; meant as an end state function."""
        ddb = RestrictedDynamoHandler()
        host_config = config.get_tenant_static_config_from_dynamo(self._host)
        if self._key is None:
            raise ValueError(
                f"ModelAdapter in an invalid state, self._key ({self._key}) is not set"
            )
        key_to_delete = ""
        config_item = None
        if not delete_root:
            config_item = self.__access_subkey_parent(
                host_config, self._key, self._default
            )
            key_to_delete = self._key.split(".")[-1]
        else:
            key_to_delete = self._key.split(".")[0]
        if not config_item:
            return False
        del config_item[key_to_delete]
        await ddb.update_static_config_for_host(
            yaml.dump(host_config), self._updated_by, self._host
        )
        return True
