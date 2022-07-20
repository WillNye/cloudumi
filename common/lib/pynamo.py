import json
from datetime import datetime, timedelta
from decimal import Decimal
from threading import local
from typing import Dict, Iterable, Mapping, Optional, Sequence, Text, Type, Union

import boto3
from boto3.dynamodb.types import Binary  # noqa
from cloudaux import get_iso_string
from pynamodax.attributes import MapAttribute
from pynamodax.connection.base import Connection
from pynamodax.connection.dax import DaxClient
from pynamodax.connection.table import MetaTable, TableConnection
from pynamodax.expressions.condition import Condition
from pynamodax.expressions.update import Action
from pynamodax.models import _T, Model, _KeyType
from pynamodax.pagination import ResultIterator
from pynamodax.settings import OperationSettings, get_settings_value

from common.config import config
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


class GlobalDaxClient(DaxClient):
    def __init__(self, session, endpoints: list[str], region_name: str):
        from amazondax import AmazonDaxClient

        self.connection = AmazonDaxClient(
            session=session, endpoints=endpoints, region_name=region_name
        )


class GlobalConnection(Connection):
    def __init__(
        self,
        region: Optional[str] = None,
        host: Optional[str] = None,
        read_timeout_seconds: Optional[float] = None,
        connect_timeout_seconds: Optional[float] = None,
        max_retry_attempts: Optional[int] = None,
        base_backoff_ms: Optional[int] = None,
        max_pool_connections: Optional[int] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        dax_write_endpoints: Optional[list[str]] = None,
        dax_read_endpoints: Optional[list[str]] = None,
        fallback_to_dynamodb: Optional[bool] = False,
        aws_account_name: Optional[str] = "tenant_data",
    ):
        from common.lib.assume_role import boto3_cached_conn

        self._tables: Dict[str, MetaTable] = {}
        self.host = host
        self._local = local()

        if not config.is_test_environment:
            session = boto3_cached_conn(
                None,
                f"_global_.accounts.{aws_account_name}",
                None,
                service_type="session",
                future_expiration_minutes=60,
                session_name="noq_dynamo_connection",
            )
        else:
            session = boto3.Session()

        self._client = session.client("dynamodb")
        self.region = region if region else get_settings_value("region")

        if connect_timeout_seconds is not None:
            self._connect_timeout_seconds = connect_timeout_seconds
        else:
            self._connect_timeout_seconds = get_settings_value(
                "connect_timeout_seconds"
            )

        if read_timeout_seconds is not None:
            self._read_timeout_seconds = read_timeout_seconds
        else:
            self._read_timeout_seconds = get_settings_value("read_timeout_seconds")

        if max_retry_attempts is not None:
            self._max_retry_attempts_exception = max_retry_attempts
        else:
            self._max_retry_attempts_exception = get_settings_value(
                "max_retry_attempts"
            )

        if base_backoff_ms is not None:
            self._base_backoff_ms = base_backoff_ms
        else:
            self._base_backoff_ms = get_settings_value("base_backoff_ms")

        if max_pool_connections is not None:
            self._max_pool_connections = max_pool_connections
        else:
            self._max_pool_connections = get_settings_value("max_pool_connections")

        if extra_headers is not None:
            self._extra_headers = extra_headers
        else:
            self._extra_headers = get_settings_value("extra_headers")

        if dax_write_endpoints is None:
            dax_write_endpoints = get_settings_value("dax_write_endpoints")

        if dax_read_endpoints is None:
            dax_read_endpoints = get_settings_value("dax_read_endpoints")

        self._dax_support = bool(dax_write_endpoints or dax_read_endpoints)
        self._dax_read_client = None
        self._dax_write_client = None

        if dax_read_endpoints:
            self._dax_read_client = GlobalDaxClient(
                session=session, endpoints=dax_read_endpoints, region_name=self.region
            )

        if dax_write_endpoints:
            self._dax_write_client = GlobalDaxClient(
                session=session, endpoints=dax_write_endpoints, region_name=self.region
            )

        if fallback_to_dynamodb is not None:
            self._fallback_to_dynamodb = fallback_to_dynamodb
        else:
            self._fallback_to_dynamodb = get_settings_value("fallback_to_dynamodb")


class GlobalTableConnection(TableConnection):
    """Connect to a global dynamo table by assuming a role into it"""

    def __init__(
        self,
        table_name: str,
        region: Optional[str] = None,
        host: Optional[str] = None,
        connect_timeout_seconds: Optional[float] = None,
        read_timeout_seconds: Optional[float] = None,
        max_retry_attempts: Optional[int] = None,
        base_backoff_ms: Optional[int] = None,
        max_pool_connections: Optional[int] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        dax_write_endpoints: Optional[list[str]] = None,
        dax_read_endpoints: Optional[list[str]] = None,
        fallback_to_dynamodb: Optional[bool] = False,
        aws_account_name: Optional[str] = "tenant_data",
    ) -> None:
        self.table_name = table_name
        self.connection = GlobalConnection(
            region=region,
            host=host,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
            max_retry_attempts=max_retry_attempts,
            base_backoff_ms=base_backoff_ms,
            max_pool_connections=max_pool_connections,
            extra_headers=extra_headers,
            dax_write_endpoints=dax_write_endpoints,
            dax_read_endpoints=dax_read_endpoints,
            fallback_to_dynamodb=fallback_to_dynamodb,
            aws_account_name=aws_account_name,
        )


class GlobalNoqModel(NoqModel):
    @classmethod
    def _get_connection(cls) -> GlobalTableConnection:
        """
        Returns a (cached) connection
        """
        if not hasattr(cls, "Meta"):
            raise AttributeError(
                "As of v1.0 PynamoDB Models require a `Meta` class.\n"
                "Model: {}.{}\n"
                "See https://pynamodb.readthedocs.io/en/latest/release_notes.html\n".format(
                    cls.__module__,
                    cls.__name__,
                ),
            )
        elif not hasattr(cls.Meta, "table_name") or cls.Meta.table_name is None:
            raise AttributeError(
                "As of v1.0 PynamoDB Models must have a table_name\n"
                "Model: {}.{}\n"
                "See https://pynamodb.readthedocs.io/en/latest/release_notes.html".format(
                    cls.__module__,
                    cls.__name__,
                ),
            )
        # For now we just check that the connection exists and (in the case of model inheritance)
        # points to the same table. In the future we should update the connection if any of the attributes differ.
        curr_time = datetime.utcnow()
        if (
            cls._connection is None
            or cls._connection.table_name != cls.Meta.table_name
            or getattr(cls, "_conn_ttl", curr_time) <= curr_time
        ):
            cls._connection = GlobalTableConnection(
                cls.Meta.table_name,
                region=cls.Meta.region,
                host=cls.Meta.host,
                connect_timeout_seconds=cls.Meta.connect_timeout_seconds,
                read_timeout_seconds=cls.Meta.read_timeout_seconds,
                max_retry_attempts=cls.Meta.max_retry_attempts,
                base_backoff_ms=cls.Meta.base_backoff_ms,
                max_pool_connections=cls.Meta.max_pool_connections,
                extra_headers=cls.Meta.extra_headers,
                dax_write_endpoints=cls.Meta.dax_write_endpoints,
                dax_read_endpoints=cls.Meta.dax_read_endpoints,
                fallback_to_dynamodb=cls.Meta.fallback_to_dynamodb,
                aws_account_name=cls.aws_account_name(),
            )
            cls._conn_ttl = curr_time + timedelta(minutes=55)

        return cls._connection

    @staticmethod
    def aws_account_name():
        return "tenant_data"


class NoqMapAttribute(MapAttribute):
    @classmethod
    def is_raw(cls):
        return cls == NoqMapAttribute

    def dict(self):  # Helper to standardize the method for converting object to dict
        return sanitize_dynamo_obj(self.as_dict())
