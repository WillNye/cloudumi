"""Configuration handling library."""
import collections
import copy
import datetime
import logging
import logging.handlers
import os
import socket
import sys
import threading
import time
import zlib
from logging import LoggerAdapter, LogRecord
from threading import Timer
from typing import Any, Dict, List, Optional, Union

import boto3
import botocore.exceptions
import logmatic
import sentry_sdk
import ujson as json
from asgiref.sync import async_to_sync
from pytz import timezone

from common.lib.aws.aws_secret_manager import get_aws_secret
from common.lib.aws.split_s3_path import split_s3_path
from common.lib.singleton import Singleton
from common.lib.yaml import yaml, yaml_safe

main_exit_flag = threading.Event()


def validate_config(dct: Dict):
    for k, v in dct.items():
        if "." in k:
            raise Exception(
                f"Configuration keys should not have dots in them. Invalid configuration key: {k}"
            )
        if (
            isinstance(dct[k], dict)
            and k not in ["logging_levels"]
            and k not in ["group_mapping"]
            and k not in ["google"]
        ):
            validate_config(dct[k])


def dict_merge(dct: dict, merge_dct: dict):
    """Recursively merge two dictionaries, including nested dicts"""
    for k, v in merge_dct.items():

        if (
            k in dct
            and isinstance(dct[k], dict)
            and isinstance(merge_dct[k], collections.Mapping)
        ):
            dict_merge(dct[k], merge_dct[k])
        else:
            # Prefer original dict values over merged dict values if they already exist
            if k not in dct.keys():
                dct[k] = merge_dct[k]
    return dct


def refresh_dynamic_config(host, ddb=None):
    if not ddb:
        # This function runs frequently. We provide the option to pass in a UserDynamoHandler
        # so we don't need to import on every invocation
        from common.lib.dynamo import UserDynamoHandler

        # TODO: Figure out host
        ddb = UserDynamoHandler(host)
    return ddb.get_dynamic_config_dict(host)


class Configuration(metaclass=Singleton):
    """Load YAML configuration files. YAML files can be extended to extend each other, to include common configuration
    values."""

    def __init__(self) -> None:
        """Initialize empty configuration."""
        self.config = {}
        self.log = None
        self.tenant_configs = collections.defaultdict(dict)

    def raise_if_invalid_aws_credentials(self):
        try:
            session_kwargs = self.get("_global_.boto3.session_kwargs", {})
            session = boto3.Session(**session_kwargs)
            session.client(
                "sts", **self.get("_global_.boto3.client_kwargs", {})
            ).get_caller_identity()
        except botocore.exceptions.NoCredentialsError:
            raise Exception(
                "We were unable to detect valid AWS credentials. Noq needs valid AWS credentials to "
                "run.\n\n"
                "For local development: Provide credentials via environment variables, in your "
                "~/.aws/credentials file, or via Weep EC2 IMDS / ECS credential provider emulation.\n\n"
                "For a production configuration, please attach an IAM role to your instance(s) or container(s) through"
                "AWS.\n\n"
                "For more information, see how the Python AWS SDK retrieves credentials here: "
                "https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html#configuring-credentials"
            )

    def load_config_from_dynamo(self, host, ddb=None, red=None):
        if not ddb:
            from common.lib.dynamo import UserDynamoHandler

            ddb = UserDynamoHandler(host=host)

        dynamic_config = refresh_dynamic_config(host, ddb)
        self.set_config_for_host(host, dynamic_config)

    def set_config_for_host(self, host, dynamic_config, red=None):
        if not red:
            from common.lib.redis import RedisHandler

            red = RedisHandler().redis_sync(host)
        if dynamic_config and dynamic_config != self.get_host_specific_key(
            "dynamic_config", host
        ):
            red.set(
                f"{host}_DYNAMIC_CONFIG_CACHE",
                json.dumps(dynamic_config),
            )
            self.get_logger("config").debug(
                {
                    "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                    "message": "Dynamic configuration changes detected and loaded",
                    "host": host,
                }
            )
            if not self.get("site_configs"):
                self.config["site_configs"] = {}
            if not self.get(f"site_configs.{host}"):
                self.config["site_configs"][host] = {}
            self.config["site_configs"][host]["dynamic_config"] = dynamic_config

    def load_dynamic_config_from_redis(
        self, log_data: Dict[str, Any], host: str, red=None
    ):
        if not red:
            from common.lib.redis import RedisHandler

            red = RedisHandler().redis_sync(host)
        dynamic_config = red.get(f"{host}_DYNAMIC_CONFIG_CACHE")
        if not dynamic_config:
            return
        dynamic_config_j = json.loads(dynamic_config)
        if self.get_host_specific_key("dynamic_config", host, {}) != dynamic_config_j:
            self.get_logger("config").debug(
                {
                    **log_data,
                    "message": "Refreshing dynamic configuration from Redis",
                }
            )
            self.config["site_configs"][host]["dynamic_config"] = dynamic_config_j

    def load_config_from_dynamo_bg_thread(self):
        """If enabled, we can load a configuration dynamically from Dynamo at a certain time interval. This reduces
        the need for code redeploys to make configuration changes"""
        from common.lib.dynamo import UserDynamoHandler
        from common.lib.redis import RedisHandler

        while threading.main_thread().is_alive():
            for host, _ in self.get("site_configs", {}).items():
                ddb = UserDynamoHandler(host=host)
                red = RedisHandler().redis_sync(host)
                self.load_config_from_dynamo(host, ddb=ddb, red=red)
            # Wait till main exit flag is set OR a fixed timeout
            if main_exit_flag.wait(
                timeout=self.get("_global_.dynamic_config.dynamo_load_interval", 60)
            ):
                break

    def load_tenant_configurations_from_redis_or_s3(self):
        """
        Initially, we're going to work with tenants on their SaaS tenant configuration. In the future, they will have
        a web interface for configuration. We want to support secure S3 storage and retrieval of tenant configuration.
        The SaaS compute that responds to tenant web requests does not need to be aware of tenant configuration until
        a web request to a tenant is received.
        The SaaS Celery compute (Caches tenant resources) does not receive tenant web requests, and it DOES need to be
        aware of tenant configuration.
        This means we can:
         1) Create a Celery task that caches tenant configuration from S3 to a Redis hash every minute or so,
        or caches specific tenant configuration on-demand. We need to take care to delete Redis hash keys for tenants
        that are no longer valid
         2) Celery workers that need all tenant configuration will pull it all in to their configuration
         3) Web hosts will pull configuration from Redis, and fall back to "s3 -> cache to redis" on demand
        :return:
        """
        # TODO: Validate layout of each Tenant configuration. It should not be able to override any other tenant config
        # or _global_ config
        # TODO: Predictable tenant configuration location and name. If web host pulls config, it should use assumerole
        # tag to restrict access to specific configuration item
        pass

    def load_tenant_configuration_from_redis_or_s3(self, host):
        """
        Loads a single tenant static configuration from S3. TODO: Support S3 access points and custom assume role
        policies to prevent one tenant from pulling another tenant's configuration
        :param host: host, aka tenant, ID
        :return:
        """
        pass

    def load_tenant_configurations_from_dynamo(self):
        """
        Loads tenant static configurations from DynamoDB and sets them in our giant configuration dictionary
        :return:
        """
        from common.lib.dynamo import RestrictedDynamoHandler

        ddb = RestrictedDynamoHandler()
        try:
            tenant_configs = ddb.get_static_config_yaml_for_all_hosts_sync()
            if not self.config.get("site_configs"):
                self.config["site_configs"] = {}
            for host, static_config in tenant_configs.items():
                self.config["site_configs"][host] = static_config
        except Exception:
            # No tenant configurations loaded.
            sentry_sdk.capture_exception()

    def __set_flag_on_main_exit(self):
        # while main thread is active, do nothing
        while threading.main_thread().is_alive():
            time.sleep(1)
        # Main thread exited, signal to other threads
        main_exit_flag.set()

    def purge_redislite_cache(self):
        """
        Purges redislite cache in primary DB periodically. This will force a cache refresh, and it is
        convenient for cases where you cannot securely run shared Redis (ie: AWS AppRunner)
        """
        if not self.get("redis.use_redislite"):
            return
        from common.lib.redis import RedisHandler

        red = RedisHandler().redis_sync("_global_")
        while threading.main_thread().is_alive():
            red.flushdb()
            # Wait till main exit flag is set OR a fixed timeout
            if main_exit_flag.wait(
                timeout=self.get("redis.purge_redislite_cache_interval", 1800)
            ):
                break

    async def merge_extended_paths(self, extends, dir_path):
        for s in extends:
            extend_config = {}
            # This decode and YAML-load a string stored in AWS Secrets Manager
            if s.startswith("AWS_SECRETS_MANAGER:"):
                secret_name = "".join(s.split("AWS_SECRETS_MANAGER:")[1:])
                extend_config = yaml.load(
                    get_aws_secret(
                        secret_name, os.environ.get("EC2_REGION", "us-east-1")
                    )
                )

            elif s.startswith("AWS_S3:s3://"):
                # TODO: Support restricting what keys are allowed to exist in this configuration. For tenant configs,
                # we need to prevent the config from overriding our other keys
                extended_config_path = s.split("AWS_S3:")[1]
                import boto3

                client = boto3.client("s3")
                bucket, key = split_s3_path(extended_config_path)
                obj = client.get_object(Bucket=bucket, Key=key)
                extend_config = yaml.load(obj["Body"].read().decode())
            else:
                try:
                    extend_path = os.path.join(dir_path, s)
                    with open(extend_path, "r") as ymlfile:
                        extend_config = yaml.load(ymlfile)
                except FileNotFoundError:
                    logging.error(f"Unable to open file: {s}", exc_info=True)

            dict_merge(self.config, extend_config)
            if extend_config.get("extends"):
                await self.merge_extended_paths(extend_config.get("extends"), dir_path)
        validate_config(self.config)

    def reload_config(self):
        from common.lib.dynamo import UserDynamoHandler
        from common.lib.redis import RedisHandler

        # We don't want to start additional background threads when we're reloading static configuration.
        while threading.main_thread().is_alive():
            async_to_sync(self.load_config)(
                allow_automatically_reload_configuration=False,
                allow_start_background_threads=False,
                load_tenant_configurations_from_dynamo=False,
            )
            # Reload dynamic configuration
            for host, _ in self.get("site_configs", {}).items():
                ddb = UserDynamoHandler(host=host)
                red = RedisHandler().redis_sync(host)
                self.load_config_from_dynamo(host, ddb=ddb, red=red)
            if not self.get("_global_.config.automatically_reload_configuration"):
                break
            # Wait till main exit flag is set OR a fixed timeout
            if main_exit_flag.wait(
                timeout=self.get("_global_.reload_static_config_interval", 60)
            ):
                break

    def get_employee_photo_url(self, user, host):
        import hashlib
        import urllib.parse

        # Try to get a custom employee photo url by formatting a string provided through configuration

        custom_employee_photo_url = self.get_host_specific_key(
            "get_employee_photo_url.custom_employee_url", host, ""
        ).format(user=user)
        if custom_employee_photo_url:
            return custom_employee_photo_url

        # Fall back to Gravatar
        gravatar_url = (
            "https://www.gravatar.com/avatar/"
            + hashlib.md5(user.lower().encode("utf-8")).hexdigest()
            + "?"
        )

        gravatar_url += urllib.parse.urlencode({"d": "mp"})
        return gravatar_url

    @staticmethod
    def get_employee_info_url(user, host):
        return None

    @staticmethod
    def get_config_location():
        config_location = os.environ.get("CONFIG_LOCATION")
        default_save_location = f"{os.curdir}/cloudumi.yaml"
        if config_location:
            if config_location.startswith("s3://"):
                import boto3

                # TODO: Need host specific configuration?
                client = boto3.client("s3")
                bucket, key = split_s3_path(config_location)
                obj = client.get_object(Bucket=bucket, Key=key)
                s3_object_content = obj["Body"].read()
                with open(default_save_location, "w") as f:
                    f.write(s3_object_content.decode())
            elif config_location.startswith("AWS_SECRETS_MANAGER:"):
                secret_name = "".join(config_location.split("AWS_SECRETS_MANAGER:")[1:])
                aws_secret_content = get_aws_secret(
                    secret_name, os.environ.get("EC2_REGION", "us-east-1")
                )
                with open(default_save_location, "w") as f:
                    f.write(aws_secret_content)
            else:
                return config_location
        config_locations: List[str] = [
            default_save_location,
            os.path.expanduser("~/.config/cloudumi/cloudumi.yaml"),
            "/etc/cloudumi/config/config.yaml",
            "example_config/example_config_development.yaml",
        ]
        for loc in config_locations:
            if os.path.exists(loc):
                return loc
        raise Exception(
            "Unable to find CloudUmi's configuration. It either doesn't exist, or "
            "CloudUmi doesn't have permission to access it. Please set the CONFIG_LOCATION environment variable "
            "to the path of the configuration, or to an s3 location with your configuration"
            "(i.e: s3://YOUR_BUCKET/path/to/config.yaml). Otherwise, CloudUmi will automatically search for the"
            f"configuration in these locations: {', '.join(config_locations)}"
        )

    async def load_config(
        self,
        allow_automatically_reload_configuration=True,
        allow_start_background_threads=True,
        load_tenant_configurations_from_dynamo=False,
    ):
        """Load configuration"""
        path = self.get_config_location()

        try:
            with open(path, "r") as ymlfile:
                self.config = yaml.load(ymlfile)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                "File not found. Please set the CONFIG_LOCATION environmental variable "
                f"to point to ConsoleMe's YAML configuration file: {e}"
            )

        extends = self.get("extends")
        dir_path = os.path.dirname(path)

        if extends:
            await self.merge_extended_paths(extends, dir_path)

        if self.get("_global_.environment") != "test":
            self.raise_if_invalid_aws_credentials()

        # We use different Timer intervals for our background threads to prevent logger objects from clashing, which
        # could cause duplicate log entries.
        if allow_start_background_threads:
            Timer(0, self.__set_flag_on_main_exit, ()).start()

        if allow_start_background_threads and self.get("_global_.redis.use_redislite"):
            t = Timer(1, self.purge_redislite_cache, ())
            t.start()
        #
        # if allow_start_background_threads and self.get(
        #     "_global_.config.load_from_dynamo", True
        # ):
        #     t = Timer(2, self.load_config_from_dynamo_bg_thread, ())
        #     t.start()

        # if allow_start_background_threads and self.get(
        #     "_global_.config.run_recurring_internal_tasks"
        # ):
        #     t = Timer(3, config_plugin.internal_functions, kwargs={"cfg": self.config})
        #     t.start()

        # if allow_automatically_reload_configuration and self.get(
        #     "_global_.config.automatically_reload_configuration"
        # ):
        #     t = Timer(4, self.reload_config, ())
        #     t.start()
        #
        # if load_tenant_configurations_from_dynamo and self.get(
        #     "_global_.config.load_tenant_configurations_from_dynamo"
        # ):
        #     t = Timer(5, self.load_tenant_configurations_from_dynamo, ())
        #     t.start()

    def get(
        self, key: str, default: Optional[Union[List[str], int, bool, str, Dict]] = None
    ) -> Any:
        """Get value for configuration entry in dot notation."""
        value = copy.deepcopy(self.config)
        # Only support keys that explicitly call out a host
        if key not in ["extends", "site_configs"] and (
            not key.startswith("site_configs.") and not key.startswith("_global_.")
        ):
            raise Exception(f"Configuration key is invalid: {key}")
        for k in key.split("."):
            try:
                value = value[k]
            except KeyError:
                return default
        return value

    def get_tenant_static_config_from_dynamo(self, host, safe=False):
        """
        Get tenant static configuration from DynamoDB. Supports zlib compressed
        configuration.
        """
        dynamodb = boto3.resource(
            "dynamodb",
            region_name=self.get_aws_region(),
            endpoint_url=self.get(
                "_global_.dynamodb_server",
                self.get("_global_.boto3.client_kwargs.endpoint_url"),
            ),
        )
        config_table = dynamodb.Table(
            self.get_dynamo_table_name("tenant_static_configs")
        )
        current_config = {}
        try:
            current_config = config_table.get_item(Key={"host": host, "id": "master"})
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return {}
        c = {}

        compressed_config = current_config.get("Item", {}).get("config", "")
        if not compressed_config:
            return c
        try:
            c = zlib.decompress(compressed_config.value)
        except Exception as e:  # noqa
            sentry_sdk.capture_exception()
            c = compressed_config
        if safe:
            return yaml_safe.load(c)
        return yaml.load(c)

    def is_host_configured(self, host) -> bool:
        """
        Check if host is configured in DynamoDB.
        """
        host_config_base_key = f"site_configs.{host}"
        if self.get(host_config_base_key):
            return True
        from common.lib.redis import RedisHandler

        red = RedisHandler().redis_sync(host)
        if red.get(f"{host}_STATIC_CONFIGURATION"):
            return True
        if self.get_tenant_static_config_from_dynamo(host):
            return True
        if self.get("_global_.environment") == "test":
            return True
        return False

    def copy_tenant_config_dynamo_to_redis(self, host):
        config_item = self.get_tenant_static_config_from_dynamo(host, safe=True)
        if config_item:
            from common.lib.redis import RedisHandler

            red = RedisHandler().redis_sync(host)
            self.tenant_configs[host]["config"] = config_item
            self.tenant_configs[host]["last_updated"] = int(time.time())
            red.set(
                f"{host}_STATIC_CONFIGURATION",
                json.dumps(self.tenant_configs[host], default=str),
            )

    def load_tenant_config_from_redis(self, host):
        from common.lib.redis import RedisHandler

        red = RedisHandler().redis_sync(host)
        return json.loads(red.get(f"{host}_STATIC_CONFIGURATION") or "{}")

    def get_host_specific_key(self, key: str, host: str, default: Any = None) -> Any:
        """
        Get a host/"tenant" specific value for configuration entry in dot notation.
        """
        # Only support keys that explicitly call out a host in development mode
        if self.get("_global_.development"):
            host_config_base_key = f"site_configs.{host}"
            # If we've defined a static config yaml file for the host, that takes precedence over
            # anything in Dynamo, even if the static config doesn't actually have the config
            # key the user is querying.
            if self.get(host_config_base_key):
                return self.get(f"{host_config_base_key}.{key}", default=default)

        # Otherwise, we need to get the config from local variable,
        # fall back to Redis cache, and lastly fall back to Dynamo
        current_time = int(time.time())
        last_updated = self.tenant_configs[host].get("last_updated", 0)
        if current_time - last_updated > 60:
            tenant_config = self.load_tenant_config_from_redis(host)
            last_updated = tenant_config.get("last_updated", 0)
            # If Redis config cache for host is newer than 60 seconds, update in-memory variables
            if current_time - last_updated < 60:
                self.tenant_configs[host]["config"] = tenant_config["config"]
                self.tenant_configs[host]["last_updated"] = last_updated
        # If local variables and Redis config cache for the host are still older than 60 seconds,
        # pull from Dynamo, update local cache, redis cache, and in-memory variables
        if current_time - last_updated > 60:
            self.copy_tenant_config_dynamo_to_redis(host)

        # Convert commented map to dictionary
        c = self.tenant_configs[host].get("config")
        if not c:
            return default
        value = json.loads(json.dumps(self.tenant_configs[host].get("config")))
        if not value:
            return default
        for k in key.split("."):
            try:
                value = value[k]
            except KeyError:
                return default
        return value

    def get_logger(self, name: Optional[str] = None) -> LoggerAdapter:
        """Get logger."""
        if self.log:
            return self.log
        if not name:
            name = self.get("_global_.application_name", "consoleme")
        level_c = self.get("_global_.logging.level", "debug")
        if level_c == "info":
            level = logging.INFO
        elif level_c == "critical":
            level = logging.CRITICAL
        elif level_c == "error":
            level = logging.ERROR
        elif level_c == "warning":
            level = logging.WARNING
        elif level_c == "debug":
            level = logging.DEBUG
        else:
            # default
            level = logging.DEBUG
        filter_c = ContextFilter()
        format_c = self.get(
            "_global_.logging.format",
            "%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)s - %(funcName)s() ] - %(message)s",
        )

        logging.basicConfig(level=level, format=format_c)
        logger = logging.getLogger(name)
        logger.addFilter(filter_c)

        extra = {"eventTime": datetime.datetime.now(timezone("US/Pacific")).isoformat()}

        # Log to stdout and disk
        if self.get("_global_.logging.stdout_enabled", True):
            logger.propagate = False
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(
                logmatic.JsonFormatter(
                    json_indent=self.get("_global_.logging.json_formatter.indent")
                )
            )
            handler.setLevel(self.get("_global_.logging.stdout.level", "DEBUG"))
            logger.addHandler(handler)
            logging_file = self.get("_global_.logging.file")
            if logging_file:
                if "~" in logging_file:
                    logging_file = os.path.expanduser(logging_file)
                os.makedirs(os.path.dirname(logging_file), exist_ok=True)
                file_handler = logging.handlers.TimedRotatingFileHandler(
                    logging_file,
                    when="d",
                    interval=1,
                    backupCount=5,
                    encoding=None,
                    delay=False,
                )
                file_handler.setFormatter(
                    logmatic.JsonFormatter(
                        json_indent=self.get("_global_.logging.json_formatter.indent")
                    )
                )
                logger.addHandler(file_handler)
        self.log = logging.LoggerAdapter(logger, extra)
        return self.log

    def set_logging_levels(self):
        default_logging_levels = {
            "asyncio": "WARNING",
            "boto3": "CRITICAL",
            "boto": "CRITICAL",
            "botocore": "CRITICAL",
            "elasticsearch.trace": "ERROR",
            "elasticsearch": "ERROR",
            "nose": "CRITICAL",
            "parso.python.diff": "WARNING",
            "raven.base.client": "WARNING",
            "s3transfer": "CRITICAL",
            "spectator.HttpClient": "WARNING",
            "spectator.Registry": "WARNING",
            "urllib3": "ERROR",
            "redislite.client": "WARNING",
            "redislite.configuration": "WARNING",
            "rediscluster.nodemanager": "WARNING",
            "rediscluster.connection": "WARNING",
            "rediscluster.client": "WARNING",
            "git.cmd": "WARNING",
            "elasticapm.metrics": "WARNING",
            "elasticapm.conf": "WARNING",
            "elasticapm.transport": "WARNING",
            "elasticapm.transport.http": "WARNING",
        }
        for logger, level in self.get(
            "_global_.logging_levels", default_logging_levels
        ).items():
            logging.getLogger(logger).setLevel(level)

    def get_aws_region(self):
        region_checks = [
            # check if set through ENV vars
            os.environ.get("EC2_REGION"),
            os.environ.get("AWS_REGION"),
            os.environ.get("AWS_DEFAULT_REGION"),
            # else check if set in config or in boto already
            boto3.DEFAULT_SESSION.region_name if boto3.DEFAULT_SESSION else None,
            boto3.Session().region_name,
            boto3.client(
                "s3", **self.get("_global_.boto3.client_kwargs", {})
            ).meta.region_name,
            "us-east-1",
        ]
        for region in region_checks:
            if region:
                return region

    def get_dynamo_table_name(
        self, table_name: str, namespace: str = "cloudumi"
    ) -> str:
        if self.get("_global_.environment") == "test" and self.get(
            "_global_.development"
        ):
            return table_name
        cluster_id_key = "_global_.deployment.cluster_id"
        cluster_id = self.get(cluster_id_key, None)
        if cluster_id is None:
            raise RuntimeError(
                f"Unable to read configuration - cannot get {cluster_id_key}"
            )
        return f"{cluster_id}_{namespace}_{table_name}"


class ContextFilter(logging.Filter):
    """Logging Filter for adding hostname to log entries."""

    hostname = socket.gethostname()

    def filter(self, record: LogRecord) -> bool:
        record.hostname = ContextFilter.hostname
        return True


CONFIG = Configuration()
async_to_sync(CONFIG.load_config)()

get = CONFIG.get
get_logger = CONFIG.get_logger
get_host_specific_key = CONFIG.get_host_specific_key
get_employee_photo_url = CONFIG.get_employee_photo_url
get_employee_info_url = CONFIG.get_employee_info_url
get_tenant_static_config_from_dynamo = CONFIG.get_tenant_static_config_from_dynamo
is_host_configured = CONFIG.is_host_configured
get_dynamo_table_name = CONFIG.get_dynamo_table_name
# Set logging levels
CONFIG.set_logging_levels()

values = CONFIG.config
region = CONFIG.get_aws_region()
hostname = socket.gethostname()
api_spec = {}
dir_ref = dir
