import sys
import threading
import time
from typing import Any, Optional

import boto3
import certifi
import redis
from cachetools import TTLCache
from redis.client import Redis
from redis.cluster import ClusterNode

import common.lib.noq_json as json
from common.config import config
from common.lib.asyncio import aio_wrapper
from common.lib.plugins import get_plugin_by_name
from common.lib.singleton import Singleton

region = config.region

cluster_mode = False
cluster_mode_nodes = []


def convert_cluster_mode_nodes_to_support_attribute_lookup(cluster_mode_nodes):
    output = []
    for n in cluster_mode_nodes:
        output.append(ClusterNode(**n))
    return output


if config.get("_global_.redis.cluster_mode.enabled"):
    cluster_mode = True
    cluster_mode_nodes = config.get(
        f"_global_.redis.cluster_mode.nodes.{region}",
        config.get("_global_.redis.cluster_mode.nodes.global", []),
    )
    if not cluster_mode_nodes:
        raise Exception("Cluster mode enabled without specifying nodes")
    cluster_mode_nodes = convert_cluster_mode_nodes_to_support_attribute_lookup(
        cluster_mode_nodes
    )

log = config.get_logger(__name__)
stats = get_plugin_by_name(config.get("_global_.plugins.metrics", "cmsaas_metrics"))()

automatically_backup_to_s3 = config.get(
    "_global_.redis.automatically_backup_to_s3.enabled", False
)
automatically_restore_from_s3 = config.get(
    "_global_.redis.automatically_restore_from_s3.enabled", False
)
# TODO: Either deprecate backup feature or make it possible to use get_session_for_tenant
s3 = boto3.resource("s3", **config.get("_global_.boto3.client_kwargs", {}))
s3_bucket = config.get("_global_.redis.automatically_backup_to_s3.bucket")
s3_folder = config.get("_global_.redis.automatically_backup_to_s3.folder")


def raise_if_key_doesnt_start_with_prefix(key: str, prefix: str):
    if (
        not isinstance(key, str)
        or not isinstance(prefix, str)
        or not key.startswith(prefix)
    ):
        log.error(
            {
                "message": "Redis Key Name doesn't start with the required prefix.",
                "key": key,
                "prefix": prefix,
            }
        )
        raise Exception("Redis Key Name doesn't start with the required prefix.")


# ToDo - Everything in ConsoleMeRedis needs to lock out unauthorized tenants
class ConsoleMeRedis(redis.RedisCluster if cluster_mode else redis.StrictRedis):
    """
    ConsoleMeRedis is a simple wrapper around redis.StrictRedis. It was created to allow Redis to be optional.
    If Redis settings are not defined in Noq's configuration, we "disable" redis. If Redis is disabled, calls to
    Redis will fail silently. If new Redis calls are added to Noq, they should be added to this class.

    ConsoleMeRedis also supports writing/retrieving data from S3 if the data is not retrievable from Redis
    """

    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        required_key_prefix = kwargs.get("required_key_prefix")
        if required_key_prefix not in cls._instances:
            with cls._lock:
                if required_key_prefix not in cls._instances:
                    instance = super().__new__(cls)
                    cls._instances[required_key_prefix] = instance
        return cls._instances[required_key_prefix]

    def __init__(self, *args, **kwargs):
        self.required_key_prefix = kwargs.pop("required_key_prefix")
        if not hasattr(self, "initialized"):
            self.enabled = True
            cache_ttl = 0 if config.get("_global_.environment") == "test" else 5
            self.cache = TTLCache(maxsize=1024, ttl=cache_ttl)
            if host := kwargs.pop("host", None):
                kwargs["host"] = host

            if not cluster_mode:
                if (
                    kwargs["host"] is None
                    or kwargs["port"] is None
                    or kwargs["db"] is None
                ):
                    self.enabled = False
            self.initialized = True
            super(ConsoleMeRedis, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        if not self.enabled:
            return None
        raise_if_key_doesnt_start_with_prefix(args[0], self.required_key_prefix)
        key = args[0]
        if key in self.cache:
            return self.cache[key]
        try:
            result = super(ConsoleMeRedis, self).get(*args, **kwargs)
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.ClusterDownError,
        ) as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": str(e),
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if not result and automatically_restore_from_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                result = obj.get()["Body"].read().decode("utf-8")
            except s3.meta.client.exceptions.NoSuchKey:
                pass
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": str(e),
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        if result:
            self.cache[key] = result
        return result

    def set(self, *args, **kwargs):
        if not self.enabled:
            return False

        raise_if_key_doesnt_start_with_prefix(args[0], self.required_key_prefix)
        try:
            result = super(ConsoleMeRedis, self).set(*args, **kwargs)
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.ClusterDownError,
        ) as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": str(e),
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if automatically_backup_to_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                obj.put(Body=str(args[1]))
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": str(e),
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result

    def setex(self, *args, **kwargs):
        if not self.enabled:
            return False
        raise_if_key_doesnt_start_with_prefix(args[0], self.required_key_prefix)
        # We do not currently support caching data in S3 with expiration (SETEX)
        try:
            result = super(ConsoleMeRedis, self).setex(*args, **kwargs)
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.ClusterDownError,
        ) as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": str(e),
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        return result

    def hmset(self, *args, **kwargs):
        if not self.enabled:
            return False
        raise_if_key_doesnt_start_with_prefix(args[0], self.required_key_prefix)
        try:
            result = super(ConsoleMeRedis, self).hmset(*args, **kwargs)
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.ClusterDownError,
        ) as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": str(e),
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if automatically_backup_to_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                # Write to S3 in a separate thread
                t = threading.Thread(
                    target=obj.put, kwargs={"Body": json.dumps(args[1])}
                )
                t.daemon = True
                t.start()
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": str(e),
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result

    def hset(self, *args, **kwargs):
        if not self.enabled:
            return False
        raise_if_key_doesnt_start_with_prefix(args[0], self.required_key_prefix)
        try:
            result = super(ConsoleMeRedis, self).hset(*args, **kwargs)
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.ClusterDownError,
        ) as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": str(e),
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if automatically_backup_to_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                try:
                    current = json.loads(obj.get()["Body"].read().decode("utf-8"))
                    current[args[1]] = args[2]
                except:  # noqa
                    current = {args[1]: args[2]}
                t = threading.Thread(
                    target=obj.put, kwargs={"Body": json.dumps(current)}
                )
                t.daemon = True
                t.start()
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": str(e),
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result

    def hget(self, *args, **kwargs):
        if not self.enabled:
            return None
        raise_if_key_doesnt_start_with_prefix(args[0], self.required_key_prefix)
        try:
            result = super(ConsoleMeRedis, self).hget(*args, **kwargs)
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.ClusterDownError,
        ) as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": str(e),
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None

        if not result and automatically_restore_from_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                current = json.loads(obj.get()["Body"].read().decode("utf-8"))
                result = current.get(args[1])
                if result:
                    self.hset(args[0], args[1], result)
            except s3.meta.client.exceptions.NoSuchKey:
                pass
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": str(e),
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result

    def hmget(self, *args, **kwargs):
        if not self.enabled:
            return None
        raise_if_key_doesnt_start_with_prefix(args[0], self.required_key_prefix)
        try:
            result = super(ConsoleMeRedis, self).hmget(*args, **kwargs)
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.ClusterDownError,
        ) as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": str(e),
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        return result

    def hgetall(self, *args, **kwargs):
        if not self.enabled:
            return None
        raise_if_key_doesnt_start_with_prefix(args[0], self.required_key_prefix)
        try:
            result = super(ConsoleMeRedis, self).hgetall(*args, **kwargs)
        except (
            redis.exceptions.ConnectionError,
            redis.exceptions.ClusterDownError,
        ) as e:
            function = (
                f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
            )
            log.error(
                {
                    "function": function,
                    "message": "Unable to perform redis operation",
                    "key": args[0],
                    "error": str(e),
                },
                exc_info=True,
            )
            stats.count(f"{function}.error")
            result = None
        if not result and automatically_restore_from_s3:
            try:
                obj = s3.Object(s3_bucket, s3_folder + f"/{args[0]}")
                result_j = obj.get()["Body"].read().decode("utf-8")
                result = json.loads(result_j)
                if result:
                    self.hmset(args[0], result)
            except s3.meta.client.exceptions.NoSuchKey:
                pass
            except Exception as e:
                function = f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}"
                log.error(
                    {
                        "function": function,
                        "message": "Unable to perform S3 operation",
                        "key": args[0],
                        "error": str(e),
                    },
                    exc_info=True,
                )
                stats.count(f"{function}.error")
        return result


class RedisHandler(metaclass=Singleton):
    def __init__(
        self,
        host: str = config.get(
            "_global_.redis.host.{}".format(region),
            config.get("_global_.redis.host.global", "localhost"),
        ),
        port: int = config.get("_global_.redis.port", 6379),
        db: int = config.get("_global_.redis.db", 0),
        password: str = config.get("_global_.secrets.redis.password", None),
        ssl: bool = config.get("_global_.redis.ssl", False),
        ssl_keyfile: str = config.get("_global_.redis.ssl_keyfile", None),
        ssl_certfile: str = config.get("_global_.redis.ssl_certfile", None),
        ssl_ca_certs: str = config.get("_global_.redis.ssl_ca_certs", certifi.where()),
    ) -> None:
        self.red = {}
        self.host = host
        self.port = port
        self.db = db
        self.enabled = True
        self.ssl = ssl
        self.ssl_keyfile = ssl_keyfile
        self.ssl_certfile = ssl_certfile
        self.ssl_ca_certs = ssl_ca_certs
        if self.host is None or self.port is None or self.db is None:
            self.enabled = False
        self.password = password

    def _get_redis(self, tenant, is_async=False):
        if cluster_mode:
            common_params = {
                "startup_nodes": cluster_mode_nodes,
                "decode_responses": True,
                "required_key_prefix": tenant,
                "skip_full_coverage_check": True,
                "ssl": self.ssl,
                "ssl_certfile": self.ssl_certfile,
                "ssl_keyfile": self.ssl_keyfile,
                "ssl_ca_certs": self.ssl_ca_certs,
                "password": self.password,
            }
        else:
            common_params = {
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "encoding": "utf-8",
                "decode_responses": True,
                "required_key_prefix": tenant,
                "ssl": self.ssl,
                "ssl_certfile": self.ssl_certfile,
                "ssl_keyfile": self.ssl_keyfile,
                "ssl_ca_certs": self.ssl_ca_certs,
                "password": self.password,
            }

        if is_async:
            return aio_wrapper(ConsoleMeRedis, **common_params)
        else:
            return ConsoleMeRedis(**common_params)

    async def redis(self, tenant, db: int = 0) -> Redis:
        if tenant not in self.red:
            self.red[tenant] = await self._get_redis(tenant, is_async=True)
        return self.red[tenant]

    def redis_sync(self, tenant, db: int = 0) -> Redis:
        if tenant not in self.red:
            self.red[tenant] = self._get_redis(tenant, is_async=False)
        return self.red[tenant]


async def redis_get(
    key: str, tenant: str, default: Optional[str] = None
) -> Optional[str]:
    raise_if_key_doesnt_start_with_prefix(key, tenant)
    red = await RedisHandler().redis(tenant)
    v = await aio_wrapper(red.get, key)
    if not v:
        return default
    return v


async def redis_hgetall(key: str, tenant: str, default=None):
    raise_if_key_doesnt_start_with_prefix(key, tenant)
    red = await RedisHandler().redis(tenant)
    v = await aio_wrapper(red.hgetall, key)
    if not v:
        return default
    return v


async def redis_hget(name: str, key: str, tenant: str, default=None):
    raise_if_key_doesnt_start_with_prefix(name, tenant)
    red = await RedisHandler().redis(tenant)
    v = await aio_wrapper(red.hget, name, key)
    if not v:
        return default
    return v


def redis_get_sync(key: str, tenant: str, default: None = None) -> Optional[str]:
    raise_if_key_doesnt_start_with_prefix(key, tenant)
    red = RedisHandler().redis_sync(tenant)
    try:
        v = red.get(key)
    except (redis.exceptions.ConnectionError, redis.exceptions.ClusterDownError):
        v = None
    if not v:
        return default
    return v


async def redis_hsetex(
    name: str, key: str, value: Any, expiration_seconds: int, tenant: str
):
    """
    Lazy way to set Redis hash keys with an expiration. Warning: Entries set here only get deleted when redis_hgetex
    is called on an expired key.

    :param name: Redis key
    :param key: Hash key
    :param value: Hash value
    :param expiration_seconds: Number of seconds to consider entry expired
    :return:
    """
    raise_if_key_doesnt_start_with_prefix(name, tenant)
    expiration = int(time.time()) + expiration_seconds
    red = await RedisHandler().redis(tenant)
    v = await aio_wrapper(
        red.hset, name, key, json.dumps({"value": value, "ttl": expiration})
    )
    return v


async def redis_hgetex(name: str, key: str, tenant: str, default=None):
    """
    Lazy way to retrieve an entry from a Redis Hash, and delete it if it's due to expire.

    :param name:
    :param key:
    :param default:
    :return:
    """
    raise_if_key_doesnt_start_with_prefix(name, tenant)
    red = await RedisHandler().redis(tenant)
    if not red.exists(name):
        return default
    result_j = await aio_wrapper(red.hget, name, key)
    if not result_j:
        return default
    result = json.loads(result_j)
    if int(time.time()) > result["ttl"]:
        red.hdel(name, key)
        return default
    return result["value"]
