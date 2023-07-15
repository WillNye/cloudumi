import operator
from functools import reduce
from typing import Any


def get_in(
    obj: dict,
    keys: str | list[str],  # type: ignore
    default=None,
    no_default=False,
):
    """Returns obj[key_0][key_1]...[key_X] where [key_0, key_1, ..., key_X] belongs to keys

    Args:
        obj (dict): dictionary to be nested
        keys (str | list[str]): list of keys or string of keys separated by '.': 'key.subkey.0'
        default (_type_, optional): default value to return. Defaults to None.
        no_default (bool, optional): Raise if keys not found. Defaults to False.

    """

    keys: list[str | int] = [
        int(key) if key.isdigit() else key
        for key in (keys.split(".") if isinstance(keys, str) else keys)
    ]

    try:
        return reduce(operator.getitem, keys, obj)
    except (KeyError, IndexError, TypeError):
        if no_default:
            raise
        return default


def set_in(
    obj: dict,
    keys: str | list[str],
    value: Any,
):
    """Set obj[key_0][key_1]...[key_X] where [key_0, key_1, ..., key_X] belongs to keys

    Recursive implementation:
    >>> if len(keys) == 1:
    >>>     obj[keys[0]] = value
    >>>     return obj
    >>> key = keys[0]
    >>> if key not in inner:
    >>>     inner[key] = dict()
    >>> set_in(inner[key], keys[1:], value)

    # return obj
    Args:
        obj (dict): dictionary to be modified
        keys (str | list[str]): list of keys or string of keys separated by '.': 'key.subkey.0'
    """
    keys = keys.split(".") if isinstance(keys, str) else keys
    inner = obj

    for key, idx in zip(keys, range(len(keys))):
        # if it is last key
        if idx == len(keys) - 1:
            inner[key] = value
        else:
            if key not in inner:
                inner[key] = dict()
            inner = inner[key]

    return obj


def delete_in(
    obj: dict,
    keys: str | list[str],
    no_default=False,
):
    """Delete obj[key_0][key_1]...[key_X] where [key_0, key_1, ..., key_X] belongs to keys


    >>> a = dict(b=dict(c=123))
    >>> delete_in(a, 'b.c') == dict(b={})

    Args:
        obj (dict): dictionary to be modified
        keys (str | list[str]): list of keys or string of keys separated by '.': 'key.subkey.0'
    """
    keys = keys.split(".") if isinstance(keys, str) else keys
    current = obj
    for key in keys[:-1]:
        try:
            current = current[key]
        except (KeyError, IndexError, TypeError):
            if no_default:
                raise
            return
    try:
        if keys[-1] in current:
            del current[keys[-1]]
    except (KeyError, IndexError, TypeError):
        if no_default:
            raise
        return
