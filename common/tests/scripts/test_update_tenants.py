import pytest

from common.scripts.update_tenants import set_deep


@pytest.mark.parametrize(
    "input, key, value, expected",
    [
        (
            # simple flat case
            {},
            "foo",
            "bar",
            {"foo": "bar"},
        ),
        (
            # nested key does not already exist
            {},
            "a.b.c.d",
            "v",
            {"a": {"b": {"c": {"d": "v"}}}},
        ),
        (
            # part of nested key exists
            {"a": {"c": {"v"}}},
            "a.b",
            "v",
            {"a": {"b": "v", "c": {"v"}}},
        ),
    ],
)
def test_set_deep(input, key, value, expected):
    set_deep(input, key, value)
    assert input == expected
