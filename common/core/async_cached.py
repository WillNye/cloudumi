import asyncio
import functools
from contextlib import AbstractContextManager
from typing import Any, Callable, MutableMapping, Optional, TypeVar

from asyncache import IdentityFunction, NullContext
from cachetools import keys

_KT = TypeVar("_KT")
_T = TypeVar("_T")


def noq_cached(
    cache: Optional[MutableMapping[_KT, Any]],
    # ignoring the mypy error to be consistent with the type used
    # in https://github.com/python/typeshed/tree/master/stubs/cachetools
    key: Callable[..., _KT] = keys.hashkey,  # type:ignore
    lock: Optional["AbstractContextManager[Any]"] = None,
    cache_none: bool = True,
) -> IdentityFunction:
    """
    Decorator to wrap a function or a coroutine with a memoizing callable
    that saves results in a cache.

    When ``lock`` is provided for a standard function, it's expected to
    implement ``__enter__`` and ``__exit__`` that will be used to lock
    the cache when gets updated. If it wraps a coroutine, ``lock``
    must implement ``__aenter__`` and ``__aexit__``.
    """
    lock = lock or NullContext()

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            async def wrapper(*args, **kwargs):
                k = key(*args, **kwargs)
                try:
                    async with lock:
                        return cache[k]

                except KeyError:
                    pass  # key not found

                val = await func(*args, **kwargs)

                try:
                    async with lock:
                        if val is not None or cache_none:
                            cache[k] = val

                except ValueError:
                    pass  # val too large

                return val

        else:

            def wrapper(*args, **kwargs):
                k = key(*args, **kwargs)
                try:
                    with lock:
                        return cache[k]

                except KeyError:
                    pass  # key not found

                val = func(*args, **kwargs)

                try:
                    with lock:
                        if val is not None or cache_none:
                            cache[k] = val

                except ValueError:
                    pass  # val too large

                return val

        return functools.wraps(func)(wrapper)

    return decorator
