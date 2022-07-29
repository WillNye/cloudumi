from typing import Any, Dict, List, Type, Union

from common.config import config
from common.lib.dynamo import RestrictedDynamoHandler
from common.lib.pydantic import BaseModel
from common.lib.yaml import yaml

UPDATED_BY = "NOQ_Automaton"
log = config.get_logger()


class ModelAdapter:
    def __init__(
        self, pydantic_model_class: Type[BaseModel], updated_by: str = UPDATED_BY
    ):
        self._model_class = pydantic_model_class
        self._model = None
        self._model_array = list()
        self._model_content = None
        self._key = None
        self._tenant = None
        self._default = None
        self._updated_by = updated_by
        # By default compare all fields; this can be set using the with_object_key member function
        self._compare_on = [x for x in self._model_class.__fields__.keys()]

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
        self, key: str, tenant: str = None, default: Any = None
    ) -> dict:
        config_item = dict()
        if tenant:
            config_item = config.get_tenant_specific_key(key, tenant, default)
            if not config_item:
                config_item: dict = (
                    config.get_tenant_static_config_from_dynamo(tenant) or dict()
                )
                config_item = self.__access_subkey(config_item, key, default)
        else:
            try:
                config_item = config.get(key, default)
            except Exception:
                pass
        return config_item

    def __nested_store(self, config_item: dict, key: str, value: BaseModel) -> dict:
        if not config_item:
            config_item = dict()

        segmented_key = key.split(".")
        if len(segmented_key) == 1:
            # Base Condition
            if isinstance(config_item.get(key), dict):
                config_item[key].update(value.dict())
            config_item[key] = dict(value)
            return config_item

        if segmented_key[0] not in config_item:
            config_item[segmented_key[0]] = dict()
        config_item[segmented_key[0]] = self.__nested_store(
            config_item[segmented_key[0]], ".".join(segmented_key[1:]), value
        )
        return config_item

    def __nested_store_array(
        self, config_item: dict, key: str, values: List[BaseModel]
    ) -> dict:
        if not config_item:
            config_item = dict()

        segmented_key = key.split(".")
        if len(segmented_key) == 1:
            # Base Condition
            if key not in config_item:
                config_item[key] = list()
            for value in values:
                similar_item = False
                for item in config_item[key]:
                    if self.__objects_similar(value.dict(), item):
                        similar_item = True

                if similar_item:
                    # Update similar item
                    config_item[key][
                        [self.filter_on(x) for x in config_item[key]].index(
                            self.filter_on(value.dict())
                        )
                    ] = value.dict()
                else:
                    # Add new item
                    config_item[key].append(value.dict())
            return config_item

        if not segmented_key[0] in config_item:
            config_item[segmented_key[0]] = dict()
        config_item[segmented_key[0]] = self.__nested_store_array(
            config_item[segmented_key[0]], ".".join(segmented_key[1:]), values
        )
        return config_item

    def __nested_delete_from_list(
        self, config_item: dict, key: str, values: List[BaseModel]
    ) -> dict:
        if not config_item:
            config_item = dict()

        segmented_key = key.split(".")
        if len(segmented_key) == 1:
            # Base Condition
            if key not in config_item:
                config_item[key] = list()
            for value in values:
                for item in config_item.get(key, []):
                    if self.__objects_similar(value.dict(), item):
                        config_item[key].remove(item)
            return config_item

        if segmented_key[0] not in config_item:
            config_item[segmented_key[0]] = dict()
        config_item[segmented_key[0]] = self.__nested_delete_from_list(
            config_item[segmented_key[0]], ".".join(segmented_key[1:]), values
        )
        return config_item

    def load_config(self, key: str, tenant: str = None, default: Any = None) -> object:
        """Required to be run before using any other functions."""
        self._key = key
        self._tenant = tenant
        self._default = default
        config_item = self.__optimistic_loader(key, tenant, default)
        if config_item and isinstance(config_item, dict):
            self._model = self._model_class.parse_obj(config_item)
            self._model_content = "one"
        elif config_item and isinstance(config_item, list):
            self._model_array = [self._model_class.parse_obj(x) for x in config_item]
            self._model_content = "many"
        else:
            self._model_content = "none"
        return self

    def add_dict(self, model_dict: dict) -> object:
        """Add dict to model array - this is a helper function to add one instance of a model to an array of models.

        :param model_dict: a dictionary representation of a model
        :return: itself
        """
        if model_dict in [x.dict() for x in self._model_array]:
            self._model_array.pop(
                [x.dict() for x in self._model_array].index(model_dict)
            )
        self._model_array.append(self._model_class.parse_obj(model_dict))
        return self

    def extend_list(self, model_dict_list: list) -> object:
        """Extend a model array - this is a helper function to add multiple instances of a model to an array of models.

        :param model_dict_list: a list of models in dictionary representation
        :return: itself
        """
        self._model_array.extend(
            [self._model_class.parse_obj(x) for x in model_dict_list]
        )
        return self

    def from_model(self, model: BaseModel) -> object:
        """Set the model to a specific pydantic model versus parsing a dict.

        :param model: a pydantic model
        :return: itself
        """
        self._model = model
        return self

    def from_dict(self, model_dict: dict) -> object:
        self._model = self._model_class.parse_obj(model_dict)
        return self

    def from_list(self, model_dict_list: list) -> object:
        self._model_array = [self._model_class.parse_obj(x) for x in model_dict_list]
        return self

    @property
    def model(self) -> Union[BaseModel, None]:
        """Easy getter"""
        if self._model is None:
            log.warning(
                "ModelAdapter may be in an invalid state. Please call load_config() first - or make sure data is loaded before using this property."
            )
        return self._model

    @property
    def dict(self) -> dict:
        """Easy getter"""
        if self._model is None:
            log.warning(
                "ModelAdapter may be in an invalid state. Please call load_config() first - or make sure data is loaded before using this property."
            )
            return dict()
        return self._model.dict()

    @property
    def models(self) -> List[BaseModel]:
        """Retrieve a list of models

        This is like the "list" function below, but it returns a list of objects versus a list of dicts.

        :return: List of models, whatever the model is
        """
        return self._model_array

    @property
    def list(self) -> list:
        """Return a list of properties under the selected key.

        :return: list of entries under configuration key with nested dicts
        """
        return [x.dict() for x in self._model_array]

    @property
    def model_content(self) -> str:
        """Return the type of content in model - either it's a single or a multiple (list) model objects

        :return: either "none", "one" or "many", set in load_config
        """
        return self._model_content

    def with_object_key(self, compare_on: List[str]) -> object:
        """Compare two objects based on a list of identifying keys as opposed to comparing the whole object.

        This is useful when trying to update a user based on user name only, when other attributes are updated

        :param comparison_identifiers: a list of keys that identify the uniqueness of this object
        :return: itself
        """
        if compare_on:
            self._compare_on = compare_on
        return self

    def __objects_similar(
        self, left: Dict[str, Any], right: Dict[str, Any], compare_on: List[str] = []
    ) -> bool:
        """Resolve uniqueness keys in left and right comparison dicts.

        This function considers a list of keys that make the object "unique", essentially creating a primary
        key of unique attributes that act as a mask or filter to update items that are not unique from a data
        perspective, but are unique based on set attributes.

        This ... could ... probably be simplified into a for loop bonanza. However, at it's core, this is just
        a basic comparison to check that all keys identified in the uniqueness_comparators are equal between
        left and right.

        :param left: dict to compare (left side)
        :param right: dict to compare (right side)
        :param uniqueness: an optional override of keys to compare, otherwise this defaults to _uniqueness_comparators
        :return: True if all uniqueness comparator identified values are equal between left and right
        """
        if not compare_on:
            compare_on = self._compare_on
        return len([c for c in compare_on if left.get(c) == right.get(c)]) == len(
            compare_on
        )

    def filter_on(self, unfiltered: Dict[str, Any]) -> Dict[str, Any]:
        """Filter `unfiltered` to only have compared items that determine the compared items' uniqueness.

        This accompanies the __resolve_unique_comparators function to effectively compare objects based
        on their uniqueness. If only some attributes contribute to making an entry unique, those effectively
        discriminate objects.

        :param unfiltered: _description_
        :return: _description_
        """
        return {x: y for x, y in unfiltered.items() if x in self._compare_on}

    def query(self, query: Dict[str, Any]) -> Union[List[BaseModel], BaseModel, None]:
        """Return all items that match the query map.

        The query dict has the following format:
        {
            "key": "value",
            .
            .
            .
        }

        A query dict can have a single entry or multiple entries.

        :param query: a dict that describes the item we would like to query and extract
        :return: a list of matches
        """
        config_item = self.__optimistic_loader(self._key, self._tenant, self._default)
        if config_item is None:
            # Maybe a log?
            return None
        elif isinstance(config_item, dict):
            return self.__objects_similar(config_item, query)
        elif isinstance(config_item, list):
            compare_on = list(query.keys())
            return [
                self._model_class.parse_obj(x)
                for x in config_item
                if self.__objects_similar(x, query, compare_on=compare_on)
            ]
        else:
            return None

    def with_query(self, query: Dict[str, Any]) -> object:
        """Set the query to a specific dict.

        :param query: a dict that describes the item we would like to query and extract
        :return: itself
        """
        self._query = query
        self._answer = self.query(self._query)
        return self

    @property
    def first(self) -> Union[BaseModel, None]:
        """Return the first item in the list of query answers.

        Requires running with_query first

        :return: the first item in the list
        """
        if isinstance(self._answer, list) and len(self._answer) > 0:
            return self._answer[0]
        else:
            raise ValueError(
                f"ModelAdapter({self._model_class}) did not find any items with the given query: {self._query}"
            )

    @property
    def last(self) -> Union[BaseModel, None]:
        """Return the last item in the list of query answers.

        Requires running with_query first

        :return: the last item in the list
        """
        if isinstance(self._answer, list) and len(self._answer) > 0:
            return self._answer[-1]
        else:
            raise ValueError(
                f"ModelAdapter({self._model_class}) did not find any items with the given query: {self._query}"
            )

    async def store_item(self) -> bool:
        """Break the chain; meant as an end state function."""
        ddb = RestrictedDynamoHandler()
        tenant_config = config.get_tenant_static_config_from_dynamo(self._tenant)
        if not self._model:
            raise ValueError(
                f"Consistency error: self._model is undefined: {self._model}"
            )
        tenant_config = self.__nested_store(tenant_config, self._key, self._model)
        await ddb.update_static_config_for_tenant(
            yaml.dump(tenant_config), self._updated_by, self._tenant
        )
        return True

    async def store_list(self) -> bool:
        ddb = RestrictedDynamoHandler()
        tenant_config = config.get_tenant_static_config_from_dynamo(self._tenant)
        if not self._model_array:
            raise ValueError(
                f"Consistency error: self._model_array is empty: {self._model_array}"
            )
        tenant_config = self.__nested_store_array(
            tenant_config, self._key, self._model_array
        )
        await ddb.update_static_config_for_tenant(
            yaml.dump(tenant_config), self._updated_by, self._tenant
        )
        return True

    async def store_item_in_list(self) -> bool:
        ddb = RestrictedDynamoHandler()
        tenant_config = config.get_tenant_static_config_from_dynamo(self._tenant)
        if not self._model:
            raise ValueError(
                f"Consistency error: self._model is undefined: {self._model}"
            )
        tenant_config = self.__nested_store_array(
            tenant_config, self._key, [self._model]
        )
        await ddb.update_static_config_for_tenant(
            yaml.dump(tenant_config), self._updated_by, self._tenant
        )
        return True

    async def delete_key(self, delete_root: bool = False) -> bool:
        """Break the chain; meant as an end state function."""
        ddb = RestrictedDynamoHandler()
        tenant_config = config.get_tenant_static_config_from_dynamo(self._tenant)
        if self._key is None:
            raise ValueError(
                f"ModelAdapter in an invalid state, self._key ({self._key}) is not set"
            )
        key_to_delete = ""
        config_item = None
        if not delete_root:
            config_item = self.__access_subkey_parent(
                tenant_config, self._key, self._default
            )
            key_to_delete = self._key.split(".")[-1]
        else:
            key_to_delete = self._key.split(".")[0]
        if not config_item:
            return False
        del config_item[key_to_delete]
        await ddb.update_static_config_for_tenant(
            yaml.dump(tenant_config), self._updated_by, self._tenant
        )
        return True

    async def delete_item_from_list(self) -> bool:
        """Delete a specific item, specified via from_dict, from a list of items.

        Note: this is to delete ONE item from a list of items. This means that the configuration
        key points to a list of items (like spoke_accounts) and we want to delete one specific item

        :return: True if the item was deleted, False if it wasn't
        """
        ddb = RestrictedDynamoHandler()
        tenant_config = config.get_tenant_static_config_from_dynamo(self._tenant)
        if not self._key:
            raise ValueError(
                f"ModelAdapter in an invalid state, self._key ({self._key}) is not set"
            )
        if not self._model:
            raise ValueError(
                f"Consistency error: self._model is undefined: {self._model}"
            )
        tenant_config = self.__nested_delete_from_list(
            tenant_config, self._key, [self._model]
        )
        await ddb.update_static_config_for_tenant(
            yaml.dump(tenant_config), self._updated_by, self._tenant
        )
        return True

    async def delete_list(self) -> bool:
        """Delete a list of items, specified via from_list method, from a list of items.

        Note: this is to delete a list of items from a list of items. This means that the configuration
        key points to a list of items (like spoke_accounts) and we want to delete a list of items
        from that list.

        :return: True if the list was deleted, False if it wasn't
        """
        ddb = RestrictedDynamoHandler()
        tenant_config = config.get_tenant_static_config_from_dynamo(self._tenant)
        if self._key is None:
            raise ValueError(
                f"ModelAdapter in an invalid state, self._key ({self._key}) is not set"
            )
        config_items = self.__access_subkey(tenant_config, self._key, self._default)
        for model in self._model_array:
            if self.filter_on(self._model.dict()) in [
                self.filter_on(x) for x in config_items
            ]:
                config_items.pop(
                    [self.filter_on(x) for x in config_items].index(
                        self.filter_on(self._model.dict())
                    )
                )
        await ddb.update_static_config_for_tenant(
            yaml.dump(tenant_config), self._updated_by, self._tenant
        )
        return True
