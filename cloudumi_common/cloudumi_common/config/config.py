"""Configuration handling library."""
import collections
import datetime
import logging
import logging.handlers
import os
import socket
import sys
import threading
import time
from logging import LoggerAdapter, LogRecord
from threading import Timer
from typing import Any, Dict, List, Optional, Union

import boto3
import botocore.exceptions
import logmatic
import ujson as json
from asgiref.sync import async_to_sync
from pytz import timezone
from ruamel.yaml import YAML

from cloudumi_common.lib.aws.aws_secret_manager import get_aws_secret
from cloudumi_common.lib.aws.split_s3_path import split_s3_path

main_exit_flag = threading.Event()

yaml = YAML(typ="safe")
yaml.preserve_quotes = True
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.width = 4096


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
        from cloudumi_common.lib.dynamo import UserDynamoHandler

        # TODO: Figure out host
        ddb = UserDynamoHandler(host)
    return ddb.get_dynamic_config_dict(host)


class Configuration(object):
    """Load YAML configuration files. YAML files can be extended to extend each other, to include common configuration
    values."""

    def __init__(self) -> None:
        """Initialize empty configuration."""
        self.config = {}
        self.log = None

    def raise_if_invalid_aws_credentials(self):
        try:
            session_kwargs = self.get("_global_.boto3.session_kwargs", {})
            session = boto3.Session(**session_kwargs)
            session.client(
                "sts", **self.get("_global_.boto3.client_kwargs", {})
            ).get_caller_identity()
        except botocore.exceptions.NoCredentialsError:
            raise Exception(
                "We were unable to detect valid AWS credentials. ConsoleMe needs valid AWS credentials to "
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
            from cloudumi_common.lib.dynamo import UserDynamoHandler

            ddb = UserDynamoHandler(host=host)
        if not red:
            from cloudumi_common.lib.redis import RedisHandler

            red = RedisHandler().redis_sync(host)

        dynamic_config = refresh_dynamic_config(host, ddb)
        if dynamic_config and dynamic_config != self.config.get_host_specific_key(
            f"site_configs.{host}.dynamic_config", host
        ):
            red.set(
                f"{host}_DYNAMIC_CONFIG_CACHE",
                json.dumps(dynamic_config),
            )
            self.get_logger("config").debug(
                {
                    "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
                    "message": "Dynamic configuration changes detected and loaded",
                }
            )
            self.config["site_configs"][host]["dynamic_config"] = dynamic_config

    def load_dynamic_config_from_redis(
        self, log_data: Dict[str, Any], host: str, red=None
    ):
        if not red:
            from cloudumi_common.lib.redis import RedisHandler

            red = RedisHandler().redis_sync(host)
        dynamic_config = red.get(f"{host}_DYNAMIC_CONFIG_CACHE")
        if not dynamic_config:
            self.get_logger("config").warning(
                {
                    **log_data,
                    "error": (
                        "Unable to retrieve Dynamic Config from Redis. "
                        "This can be safely ignored if your dynamic config is empty."
                    ),
                }
            )
            return
        dynamic_config_j = json.loads(dynamic_config)
        if (
            self.config.get_host_specific_key(
                f"site_configs.{host}.dynamic_config", host, {}
            )
            != dynamic_config_j
        ):
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
        from cloudumi_common.lib.dynamo import UserDynamoHandler
        from cloudumi_common.lib.redis import RedisHandler

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
        from cloudumi_common.lib.redis import RedisHandler

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
        # We don't want to start additional background threads when we're reloading static configuration.
        while threading.main_thread().is_alive():
            async_to_sync(self.load_config)(
                allow_automatically_reload_configuration=False,
                allow_start_background_threads=False,
            )
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
            f"site_configs.{host}.get_employee_photo_url.custom_employee_url", host, ""
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
        # TODO: This is only called once, so I need to pull a massive configuration for all customers after
        # verifying validity

        # And have to re-pull it every once in a while
        # Customers should NOT be allowed to mess up the configuration
        # Dynamic configuration for customer turns into advanced configuration  for them

        config_location = os.environ.get("CONFIG_LOCATION")
        default_save_location = f"{os.curdir}/cloudumi.yaml"
        if config_location:
            if config_location.startswith("s3://"):
                import boto3

                # TODO: Need host specific configuration?
                client = boto3.client("s3")
                bucket, key = split_s3_path(config_location)
                obj = client.get_object(Bucket=bucket, Key=key, host="_global_")
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

        if allow_start_background_threads and self.get(
            "_global_.config.load_from_dynamo", True
        ):
            t = Timer(2, self.load_config_from_dynamo_bg_thread, ())
            t.start()

        # if allow_start_background_threads and self.get(
        #     "_global_.config.run_recurring_internal_tasks"
        # ):
        #     t = Timer(3, config_plugin.internal_functions, kwargs={"cfg": self.config})
        #     t.start()

        if allow_automatically_reload_configuration and self.get(
            "_global_.config.automatically_reload_configuration"
        ):
            t = Timer(4, self.reload_config, ())
            t.start()

    def get(
        self, key: str, default: Optional[Union[List[str], int, bool, str, Dict]] = None
    ) -> Any:
        """Get value for configuration entry in dot notation."""
        value = self.config
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

    def get_host_specific_key(self, key: str, host: str, default: Any = None) -> Any:
        """
        Get a host/"tenant" specific value for configuration entry in dot notation.
        """
        # TODO: Load config from S3 or DDB and cache for 60s
        # TODO: Verify signing key upon loading
        # TODO: Verify model
        # REF: Regex search: c|onfig.get\(f\"site_configs.\{host\}.([\.a-zA-Z0-9\_\-]+)"
        if not key.startswith(f"site_configs.{host}"):
            raise Exception(f"Configuration key is invalid: {key}")
        return self.get(key, default=default)

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

# Set logging levels
CONFIG.set_logging_levels()

values = CONFIG.config
region = CONFIG.get_aws_region()
hostname = socket.gethostname()
api_spec = {}
dir_ref = dir
