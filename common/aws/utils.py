from typing import Dict, Optional

from policy_sentry.util.arns import parse_arn

from common.config import config

log = config.get_logger()


def get_resource_tag(
    resource: Dict,
    key: str,
    is_list: Optional[bool] = False,
    default: Optional[any] = None,
) -> any:
    """
    Retrieves and parses the value of a provided AWS tag.
    :param resource: An AWS resource dictionary
    :param key: key of the tag
    :param is_list: The value for the key is a list type
    :param default: Default value is tag not found
    :return:
    """
    for tag in resource.get("Tags", resource.get("tags", [])):
        if tag.get("Key") == key:
            val = tag.get("Value")
            if is_list:
                return set([] if not val else val.split(":"))
            return val
    return default


class ResourceSummary:
    def __init__(
        self,
        host: str,
        arn: str,
        account: str,
        partition: str,
        service: str,
        region: str,
        resource_type: str,
        name: str,
        resource_path: str = None,
    ):
        self.host = host
        self.arn = arn
        self.account = account
        self.partition = partition
        self.service = service
        self.region = region
        self.resource_type = resource_type
        self.name = name
        self.path = resource_path

    @classmethod
    async def set(cls, host: str, arn: str) -> "ResourceSummary":
        from common.lib.aws.utils import (
            get_bucket_location_with_fallback,
            get_resource_account,
        )

        parsed_arn = parse_arn(arn)
        parsed_arn["arn"] = arn

        if not parsed_arn["account"]:
            parsed_arn["account"] = await get_resource_account(arn, host)
            if not parsed_arn["account"]:
                raise ValueError("Resource account not found")

        if parsed_arn["service"] == "s3":
            parsed_arn["name"] = parsed_arn.pop("resource", "")
            parsed_arn["resource_type"] = parsed_arn["service"]  # Maybe bucket?

            if not parsed_arn["region"]:
                parsed_arn["region"] = await get_bucket_location_with_fallback(
                    parsed_arn["name"], parsed_arn["account"], host
                )
        else:
            if not parsed_arn["region"]:
                parsed_arn["region"] = config.region

            if resource_path := parsed_arn.pop("resource_path", ""):
                parsed_arn["name"] = resource_path
                parsed_arn["resource_type"] = parsed_arn.pop("resource", "")
            else:
                parsed_arn["name"] = parsed_arn.pop("resource", "")
                parsed_arn["resource_type"] = parsed_arn["service"]

        return cls(host, **parsed_arn)
