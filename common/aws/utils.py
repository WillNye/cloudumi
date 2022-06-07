from typing import Dict, Optional


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
