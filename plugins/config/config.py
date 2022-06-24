import os
from typing import List

from common.lib.aws.aws_secret_manager import get_aws_secret


def split_s3_path(s3_path):
    path_parts = s3_path.replace("s3://", "").split("/")
    b = path_parts.pop(0)
    k = "/".join(path_parts)
    return b, k


class Config:
    @staticmethod
    def get_config_location():
        # TODO: This is only called once, so I need to pull a massive configuration for all customers after
        # verifying validity

        # And have to re-pull it every once in a while
        # Customers should NOT be allowed to mess up the configuration
        # Dynamic configuration for customer turns into advanced configuration  for them

        config_location = os.environ.get("CONFIG_LOCATION")
        default_save_location = f"{os.curdir}/consoleme.yaml"
        if config_location:
            if config_location.startswith("s3://"):
                import boto3

                # TODO: Need tenant specific configuration?
                client = boto3.client("s3")
                bucket, key = split_s3_path(config_location)
                obj = client.get_object(Bucket=bucket, Key=key, tenant="_global_")
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
            os.path.expanduser("~/.config/noq/config.yaml"),
            "/etc/noq/config/config.yaml",
            "example_config/example_config_development.yaml",
        ]
        for loc in config_locations:
            if os.path.exists(loc):
                return loc
        raise Exception(
            "Unable to find app configuration. It either doesn't exist, or "
            "We don't have permission to access it. Please set the CONFIG_LOCATION environment variable "
            "to the path of the configuration, or to an s3 location with your configuration"
            "(i.e: s3://YOUR_BUCKET/path/to/config.yaml). Otherwise, ConsoleMe will automatically search for the"
            f"configuration in these locations: {', '.join(config_locations)}"
        )

    @staticmethod
    def internal_functions(cfg=None):
        cfg = cfg or {}

    @staticmethod
    def is_contractor(user):
        return False


def init():
    """Initialize the Config plugin."""
    return Config()
