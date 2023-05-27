import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import orjson
import ujson
from deepdiff.model import PrettyOrderedSet


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (frozenset, set, PrettyOrderedSet)):
            return list(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.timestamp()
        if isinstance(obj, Exception):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def dumps(
    obj: any,
    ensure_ascii: bool = True,
    double_precision: int = 9,
    encode_html_chars: bool = False,
    escape_forward_slashes: bool = False,
    sort_keys: bool = False,
    indent: int = 0,
    **kwargs
) -> str:
    try:
        # Try orjson first
        result = orjson.dumps(
            obj, indent=indent, option=orjson.OPT_NON_STR_KEYS
        ).decode()
    except TypeError:
        try:
            # Try ujson next
            result = ujson.dumps(
                obj,
                ensure_ascii=ensure_ascii,
                double_precision=double_precision,
                encode_html_chars=encode_html_chars,
                escape_forward_slashes=escape_forward_slashes,
                sort_keys=sort_keys,
                indent=indent,
                **kwargs
            )
        except TypeError:
            # Fallback to the slower json library
            result = json.dumps(
                obj,
                cls=SetEncoder,
                ensure_ascii=ensure_ascii,
                sort_keys=sort_keys,
                indent=indent,
                **kwargs
            )
    return result


def loads(s: str, **kwargs) -> any:
    try:
        # Try orjson first
        result = orjson.loads(s)
    except ValueError:
        try:
            # Try ujson next
            result = ujson.loads(s, **kwargs)
        except ValueError:
            # Fallback to the json library
            result = json.loads(s, **kwargs)
    return result


def load(f, **kwargs) -> any:
    try:
        result = ujson.load(f, **kwargs)
    except ValueError:
        result = json.load(f, **kwargs)
    return result


def dump(obj, f, **kwargs) -> any:
    try:
        result = ujson.dump(obj, f, **kwargs)
    except ValueError:
        result = json.dump(obj, f, **kwargs)
    return result
