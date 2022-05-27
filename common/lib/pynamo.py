import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Iterable, Optional, Sequence, Text, Type, Union

from boto3.dynamodb.types import Binary  # noqa
from cloudaux import get_iso_string
from pynamodax.attributes import MapAttribute
from pynamodax.expressions.condition import Condition
from pynamodax.expressions.update import Action
from pynamodax.models import _T, Model, _KeyType
from pynamodax.pagination import ResultIterator
from pynamodax.settings import OperationSettings

from common.lib.asyncio import aio_wrapper

DYNAMO_EMPTY_STRING = "---DYNAMO-EMPTY-STRING---"
DYNAMODB_EMPTY_DECIMAL = Decimal(0)


def sanitize_dynamo_obj(
    obj: Union[
        list[dict[str, Union[Decimal, str]]],
        dict[str, Union[Decimal, str]],
        str,
        Decimal,
    ],
) -> Union[int, dict[str, Union[int, str]], str, list[dict[str, Union[int, str]]]]:
    """Traverse a potentially nested object and replace all Dynamo placeholders with actual empty strings
    Args:
        obj (object)
    Returns:
        object: Object with original empty strings
    """
    if isinstance(obj, dict):
        for k in ["aws:rep:deleting", "aws:rep:updateregion", "aws:rep:updatetime"]:
            if k in obj.keys():
                del obj[k]
        return {k: sanitize_dynamo_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_dynamo_obj(elem) for elem in obj]
    else:
        if isinstance(obj, Binary):
            obj = obj.value
        elif str(obj) == DYNAMO_EMPTY_STRING:
            obj = ""
        elif isinstance(obj, Decimal):
            obj = int(obj)
        return obj


class NoqModel(Model):
    def dict(self) -> dict:
        return sanitize_dynamo_obj(super(NoqModel, self).dict())

    def dump_json_attr(self, attr: dict) -> str:
        return json.dumps(attr, default=self._json_encode_timestamps)

    async def save(
        self,
        condition: Optional[Condition] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> Dict[str, any]:
        return await aio_wrapper(super(NoqModel, self).save, condition, settings)

    async def update(
        self,
        actions: list[Action],
        condition: Optional[Condition] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> any:
        return await aio_wrapper(
            super(NoqModel, self).update, actions, condition, settings
        )

    async def delete(
        self,
        condition: Optional[Condition] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> any:
        return await aio_wrapper(super(NoqModel, self).delete, condition, settings)

    @staticmethod
    def _json_encode_timestamps(field: datetime) -> str:
        """Solve those pesky timestamps and JSON annoyances."""
        if isinstance(field, datetime):
            return get_iso_string(field)

    @classmethod
    async def get(
        cls: Type[_T],
        hash_key: _KeyType,
        range_key: Optional[_KeyType] = None,
        consistent_read: bool = False,
        attributes_to_get: Optional[Sequence[Text]] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> _T:
        return await aio_wrapper(
            super(NoqModel, cls).get,
            hash_key,
            range_key,
            consistent_read,
            attributes_to_get,
            settings,
        )

    @classmethod
    async def scan(
        cls: Type[_T],
        filter_condition: Optional[Condition] = None,
        segment: Optional[int] = None,
        total_segments: Optional[int] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Dict[str, any]]] = None,
        page_size: Optional[int] = None,
        consistent_read: Optional[bool] = None,
        index_name: Optional[str] = None,
        rate_limit: Optional[float] = None,
        attributes_to_get: Optional[Sequence[str]] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> ResultIterator[_T]:
        return await aio_wrapper(
            super(NoqModel, cls).scan,
            filter_condition,
            segment,
            total_segments,
            limit,
            last_evaluated_key,
            page_size,
            consistent_read,
            index_name,
            rate_limit,
            attributes_to_get,
            settings,
        )

    @classmethod
    async def query(
        cls: Type[_T],
        hash_key: _KeyType,
        range_key_condition: Optional[Condition] = None,
        filter_condition: Optional[Condition] = None,
        consistent_read: bool = False,
        index_name: Optional[str] = None,
        scan_index_forward: Optional[bool] = None,
        limit: Optional[int] = None,
        last_evaluated_key: Optional[Dict[str, Dict[str, any]]] = None,
        attributes_to_get: Optional[Iterable[str]] = None,
        page_size: Optional[int] = None,
        rate_limit: Optional[float] = None,
        settings: OperationSettings = OperationSettings.default,
    ) -> ResultIterator[_T]:
        return await aio_wrapper(
            super(NoqModel, cls).query,
            hash_key,
            range_key_condition,
            filter_condition,
            consistent_read,
            index_name,
            scan_index_forward,
            limit,
            last_evaluated_key,
            attributes_to_get,
            page_size,
            rate_limit,
            settings,
        )


class NoqMapAttribute(MapAttribute):
    @classmethod
    def is_raw(cls):
        return cls == NoqMapAttribute

    def dict(self):  # Helper to standardize the method for converting object to dict
        return sanitize_dynamo_obj(self.as_dict())
