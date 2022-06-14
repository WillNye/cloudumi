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
        parent_name: str = None,
    ):
        self.host = host
        self.arn = arn
        self.account = account
        self.partition = partition
        self.service = service
        self.region = region
        self.resource_type = resource_type
        self.name = name
        self.parent_name = parent_name

    @classmethod
    async def set(cls, host: str, arn: str) -> "ResourceSummary":
        from common.lib.aws.utils import (
            get_bucket_location_with_fallback,
            get_resource_account,
        )

        parsed_arn = parse_arn(arn)
        parsed_arn["arn"] = arn
        account_provided = bool(parsed_arn["account"])

        if not account_provided:
            arn_as_resource = arn
            if parsed_arn["service"] == "s3" and not account_provided:
                arn_as_resource = arn_as_resource.replace(
                    f"/{parsed_arn['resource_path']}", ""
                )

            parsed_arn["account"] = await get_resource_account(arn_as_resource, host)
            if not parsed_arn["account"]:
                raise ValueError("Resource account not found")

        if parsed_arn["service"] == "s3":
            parsed_arn["name"] = parsed_arn.pop("resource_path", None)
            if not account_provided:  # Either a bucket or an object
                if parsed_arn["name"]:
                    bucket_name = parsed_arn.pop("resource", "")
                    parsed_arn["resource_type"] = "object"
                    parsed_arn["parent_name"] = bucket_name
                else:
                    bucket_name = parsed_arn.pop("resource", "")
                    parsed_arn["resource_type"] = "bucket"
                    parsed_arn["name"] = bucket_name

                parsed_arn["region"] = await get_bucket_location_with_fallback(
                    bucket_name, parsed_arn["account"], host
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
