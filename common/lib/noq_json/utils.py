import json
from datetime import datetime
from decimal import Decimal

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
    return ujson.dumps(
        obj,
        ensure_ascii,
        double_precision,
        encode_html_chars,
        escape_forward_slashes,
        sort_keys,
        indent,
        **kwargs
    )


def loads(s: str, **kwargs) -> any:
    return ujson.loads(s, **kwargs)
