from typing import Any

import pytest

from common.lib.dictutils import delete_in, get_in, set_in


class TestSetIn:
    @pytest.mark.parametrize(
        "items",
        [
            (dict(a=dict(b=dict())), ["a", "b", "c"], 3, dict(a=dict(b=dict(c=3)))),
            (dict(a=dict(b=3)), "a.c", dict(b=2), dict(a=dict(b=3, c=dict(b=2)))),
            (
                dict(a=dict(b=[])),
                "a.b",
                3,
                dict(a=dict(b=3)),
            ),
            (dict(a=dict(b=3)), "a.c.b", 1, dict(a=dict(b=3, c=dict(b=1)))),
        ],
    )
    def test_set_in(self, items: tuple[dict, str | list[str], Any, Any]):
        obj, keys, value, expected = items
        set_in(obj, keys, value)
        assert obj == expected


class TestGetIn:
    @pytest.mark.parametrize(
        "items",
        [
            (dict(a=dict(b=3)), ["a", "b"], 3),
            (dict(a=dict(b=3)), "a.b", 3),
            (dict(a=dict(b=3)), "a.c", None),
            (dict(a=dict(b=3)), "a.c.b", None),
            (dict(a=dict(b=[3, 4])), "a.b.0", 3),
        ],
    )
    def test_get_in(self, items: tuple[dict, str | list[str], Any]):
        obj, keys, expected = items
        result = get_in(obj, keys)
        assert result == expected


class TestDeleteIn:
    @pytest.mark.parametrize(
        "items",
        [
            (dict(a=dict(b=3)), ["a", "b"], dict(a={})),
            (dict(a=dict(b=3)), "a.b", dict(a={})),
            (dict(a=dict(b=3)), "a.c", dict(a=dict(b=3))),
            (dict(a=dict(b=3)), "a.c.b", dict(a=dict(b=3))),
        ],
    )
    def test_delete_in(self, items):
        obj, keys, expected = items
        delete_in(obj, keys)
        assert obj == expected
