"""Configuration handling library."""
import datetime
import logging
import logging.handlers
import os
import socket
import sys
import threading
import time
from collections import defaultdict
from collections.abc import Mapping
from logging import LoggerAdapter, LogRecord
from threading import Timer
from typing import Any, Dict, List, Optional, Union

import boto3
import botocore.exceptions
import logmatic
from pytz import timezone

import common.lib.noq_json as json
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

        if k in dct and isinstance(dct[k], dict) and isinstance(merge_dct[k], Mapping):
            dict_merge(dct[k], merge_dct[k])
        else:
            # Prefer original dict values over merged dict values if they already exist
            if k not in dct.keys():
                dct[k] = merge_dct[k]
    return dct


class Configuration(metaclass=Singleton):
    """Load YAML configuration files. YAML files can be extended to extend each other, to include common configuration
    values."""

    def __init__(self) -> None:
        """Initialize empty configuration."""
        self.config = {}
        self.log = None
        self.tenant_configs = defaultdict(dict)

    def raise_if_invalid_aws_credentials(self):
        try:
            region = self.get_aws_region()
            session_kwargs = self.get("_global_.boto3.session_kwargs", {})
            session = boto3.Session(**session_kwargs)
            identity = session.client(
                "sts",
                region_name=region,
                endpoint_url=f"https://sts.{region}.amazonaws.com",
                **self.get("_global_.boto3.client_kwargs", {}),
            ).get_caller_identity()
            identity_arn_with_session_name = (
                identity["Arn"]
                .replace(":sts:", ":iam:")
                .replace("assumed-role", "role")
            )
            identity_arn = "/".join(identity_arn_with_session_name.split("/")[0:2])
            node_role_arn = self.get("_global_.integrations.aws.node_role", {})
            if identity_arn != node_role_arn:
                raise Exception(
                    f"AWS credentials are not set to the correct role. Expected {node_role_arn}, got {identity_arn}"
                )
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

    def load_dynamic_config_from_redis(
        self, log_data: Dict[str, Any], tenant: str, red=None
    ):
        if not red:
            from common.lib.redis import RedisHandler

            red = RedisHandler().redis_sync(tenant)
        dynamic_config = red.get(f"{tenant}_DYNAMIC_CONFIG_CACHE")
        if not dynamic_config:
            return
        dynamic_config_j = json.loads(dynamic_config)
        if (
            self.get_tenant_specific_key("dynamic_config", tenant, {})
            != dynamic_config_j
        ):
            self.get_logger("config").debug(
                {
                    **log_data,
                    "message": "Refreshing dynamic configuration from Redis",
                }
            )
            self.config["site_configs"][tenant]["dynamic_config"] = dynamic_config_j

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
         3) Web tenants will pull configuration from Redis, and fall back to "s3 -> cache to redis" on demand
        :return:
        """
        # TODO: Validate layout of each Tenant configuration. It should not be able to override any other tenant config
        # or _global_ config
        # TODO: Predictable tenant configuration location and name. If web host pulls config, it should use assumerole
        # tag to restrict access to specific configuration item
        pass

    def load_tenant_configuration_from_redis_or_s3(self, tenant):
        """
        Loads a single tenant static configuration from S3. TODO: Support S3 access points and custom assume role
        policies to prevent one tenant from pulling another tenant's configuration
        :param tenant: tenant, aka tenant, ID
        :return:
        """
        pass

    def __set_flag_on_main_exit(self):
        # while main thread is active, do nothing
        while threading.main_thread().is_alive():
            time.sleep(1)
        # Main thread exited, signal to other threads
        main_exit_flag.set()

    def merge_extended_paths(self, extends, dir_path):
        for s in extends:
            extend_config = {}
            # This decode and YAML-load a string stored in AWS Secrets Manager
            if s.startswith("AWS_SECRETS_MANAGER:"):
                secret_arn = "".join(s.split("AWS_SECRETS_MANAGER:")[1:])
                extend_config = yaml.load(get_aws_secret(secret_arn))

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
                self.merge_extended_paths(extend_config.get("extends"), dir_path)
        validate_config(self.config)

    def is_test_environment(self) -> bool:
        return self.get("_global_.environment") == "test"

    def get_employee_photo_url(self, user, tenant):
        import hashlib
        import urllib.parse

        # Try to get a custom employee photo url by formatting a string provided through configuration

        custom_employee_photo_url = self.get_tenant_specific_key(
            "get_employee_photo_url.custom_employee_url", tenant, ""
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
    def get_employee_info_url(user, tenant):
        return None

    @staticmethod
    def get_config_location():
        config_location = os.environ.get("CONFIG_LOCATION")
        default_save_location = f"{os.curdir}/cloudumi.yaml"
        if config_location:
            if config_location.startswith("s3://"):
                import boto3

                # TODO: Need tenant specific configuration?
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

    def load_config(
        self,
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
                f"to point to Noq's YAML configuration file: {e}"
            )

        extends = self.get("extends")
        dir_path = os.path.dirname(path)

        if extends:
            self.merge_extended_paths(extends, dir_path)

        if not self.is_test_environment():
            self.raise_if_invalid_aws_credentials()

        # We use different Timer intervals for our background threads to prevent logger objects from clashing, which
        # could cause duplicate log entries.
        if allow_start_background_threads:
            Timer(0, self.__set_flag_on_main_exit, ()).start()

    def get(
        self, key: str, default: Optional[Union[List[str], int, bool, str, Dict]] = None
    ) -> Any:
        """Get value for configuration entry in dot notation."""
        value = default
        # Only support keys that explicitly call out a tenant
        if key not in ["extends", "site_configs"] and (
            not key.startswith("site_configs.") and not key.startswith("_global_.")
        ):
            raise Exception(f"Configuration key is invalid: {key}")
        nested = False
        for k in key.split("."):
            try:
                if nested:
                    value = value[k]
                else:
                    value = self.config[k]
                    nested = True
            except KeyError:
                return default
        return value

    def get_global_s3_bucket(self, bucket_name) -> str:
        return self.get(f"_global_.s3_buckets.{bucket_name}")

    def get_tenant_static_config_from_dynamo(self, tenant, safe=False):
        """
        Get tenant static configuration from DynamoDB.
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
            current_config = config_table.get_item(
                Key={"tenant": tenant, "id": "master"}
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                return {}
        c = {}

        tenant_config = current_config.get("Item", {}).get("config", "")
        if not tenant_config:
            return c

        if safe:
            return yaml_safe.load(tenant_config)
        return yaml.load(tenant_config)

    def is_tenant_configured(self, tenant) -> bool:
        """
        Check if tenant is configured in DynamoDB.
        """
        tenant_config_base_key = f"site_configs.{tenant}"
        if self.get(tenant_config_base_key):
            return True
        from common.lib.redis import RedisHandler

        red = RedisHandler().redis_sync(tenant)
        if red.get(f"{tenant}_STATIC_CONFIGURATION"):
            return True
        elif self.get_tenant_static_config_from_dynamo(tenant):
            return True
        else:
            return self.is_test_environment()

    def copy_tenant_config_dynamo_to_redis(self, tenant):
        config_item = self.get_tenant_static_config_from_dynamo(tenant, safe=True)
        if config_item:
            from common.lib.redis import RedisHandler

            red = RedisHandler().redis_sync(tenant)
            self.tenant_configs[tenant]["config"] = config_item
            self.tenant_configs[tenant]["last_updated"] = int(time.time())
            red.set(
                f"{tenant}_STATIC_CONFIGURATION",
                json.dumps(self.tenant_configs[tenant], default=str),
            )

    def load_tenant_config_from_redis(self, tenant):
        from common.lib.redis import RedisHandler

        red = RedisHandler().redis_sync(tenant)
        return json.loads(red.get(f"{tenant}_STATIC_CONFIGURATION") or "{}")

    def get_tenant_specific_key(
        self, key: str, tenant: str, default: Any = None
    ) -> Any:
        """
        Get a tenant specific value for configuration entry in dot notation.
        """
        # Only support keys that explicitly call out a tenant in development mode

        if self.get("_global_.development"):
            static_config_key = f"site_configs.{tenant}.{key}"
            # If we've defined a static config yaml file for the tenant, that takes precedence over
            # anything in Dynamo, even if the static config doesn't actually have the config
            # key the user is querying.
            if self.get(static_config_key):
                return self.get(static_config_key, default=default)

        # Otherwise, we need to get the config from local variable,
        # fall back to Redis cache, and lastly fall back to Dynamo
        current_time = int(time.time())
        last_updated = self.tenant_configs[tenant].get("last_updated", 0)
        if current_time - last_updated > 5:
            tenant_config = self.load_tenant_config_from_redis(tenant)
            last_updated = int(tenant_config.get("last_updated", 0))
            # If Redis config cache for tenant is newer than 60 seconds, update in-memory variables
            if current_time - last_updated < 60:
                self.tenant_configs[tenant]["config"] = tenant_config["config"]
                self.tenant_configs[tenant]["last_updated"] = last_updated
        # If local variables and Redis config cache for the tenant are still older than 60 seconds,
        # pull from Dynamo, update local cache, redis cache, and in-memory variables
        if current_time - last_updated > 60:
            self.copy_tenant_config_dynamo_to_redis(tenant)

        # Convert commented map to dictionary
        c = self.tenant_configs[tenant].get("config")
        if not c:
            return default

        value = json.loads(json.dumps(self.tenant_configs[tenant].get("config")))
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
            name = self.get("_global_.application_name", "noq")
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
            "amazondax": "WARNING",
            "asyncio": "WARNING",
            "boto3": "CRITICAL",
            "boto": "CRITICAL",
            "botocore": "CRITICAL",
            "elasticsearch.trace": "ERROR",
            "elasticsearch": "ERROR",
            "nose": "CRITICAL",
            "parso.python.diff": "WARNING",
            "pynamodb": "WARNING",
            "raven.base.client": "WARNING",
            "s3transfer": "CRITICAL",
            "spectator.HttpClient": "WARNING",
            "spectator.Registry": "WARNING",
            "urllib3": "ERROR",
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
        if self.is_test_environment() and self.get("_global_.development"):
            return table_name
        cluster_id_key = "_global_.deployment.cluster_id"
        cluster_id = self.get(cluster_id_key, None)
        if cluster_id is None:
            raise RuntimeError(
                f"Unable to read configuration - cannot get {cluster_id_key}"
            )
        return f"{cluster_id}_{namespace}_{table_name}_v2"

    def dynamodb_host(self):
        return self.get(
            "_global_.dynamodb_server",
            self.get("_global_.boto3.client_kwargs.endpoint_url"),
        )

    def get_dax_endpoints(self):
        return self.get("_global_.dax_endpoints", [])


class ContextFilter(logging.Filter):
    """Logging Filter for adding hostname to log entries."""

    hostname = socket.gethostname()

    def filter(self, record: LogRecord) -> bool:
        record.hostname = ContextFilter.hostname
        return True


CONFIG = Configuration()
CONFIG.load_config()

get = CONFIG.get
get_logger = CONFIG.get_logger
get_tenant_specific_key = CONFIG.get_tenant_specific_key
get_employee_photo_url = CONFIG.get_employee_photo_url
get_employee_info_url = CONFIG.get_employee_info_url
get_tenant_static_config_from_dynamo = CONFIG.get_tenant_static_config_from_dynamo
is_tenant_configured = CONFIG.is_tenant_configured
get_dynamo_table_name = CONFIG.get_dynamo_table_name
get_global_s3_bucket = CONFIG.get_global_s3_bucket
is_test_environment = CONFIG.is_test_environment
# Set logging levels
CONFIG.set_logging_levels()

values = CONFIG.config
region = CONFIG.get_aws_region()
dax_endpoints = CONFIG.get_dax_endpoints()
dynamodb_host = CONFIG.dynamodb_host()
hostname = socket.gethostname()
api_spec = {}
dir_ref = dir
