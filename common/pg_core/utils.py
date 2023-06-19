from itertools import chain, islice
from typing import Iterable, List, Type, TypeVar

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from common.config.globals import ASYNC_PG_SESSION

T = TypeVar("T")


def batch(iterable: Iterable[T], size: int) -> Iterable[List[T]]:
    """
    Divide the input iterable into batches of the given size.

    :param iterable: An iterable to be divided into batches
    :param size: The size of each batch
    :return: An iterable of lists, where each list is a batch
    """
    iterator = iter(iterable)
    for first in iterator:
        yield list(chain([first], islice(iterator, size - 1)))


async def bulk_add(instance_list: List[T]) -> List[T]:
    """
    Add a list of instances to the database in batches.

    :param instance_list: A list of instances to be added to the database
    :return: The list of instances added to the database
    """
    batch_size = 100

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for instance_batch in batch(instance_list, batch_size):
                session.add_all(instance_batch)

    return instance_list


async def bulk_delete(instance_list: List[T], as_query: bool = True) -> None:
    """Delete a list of instances from the database in batches.

    The purpose of to delete by object is to not only delete the object,
     but it's related objects as part of a cascade.
    It's slower but that's fine if you're deleting < 1000 objects,
     and it's way easier to read

    :param instance_list: A list of instances to be deleted from the database
    :param as_query: Whether the deletion should occur on the object itself or as a delete by query
    """
    batch_size = 100
    instance_type = type(instance_list[0])
    assert all(isinstance(instance, instance_type) for instance in instance_list)

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for instance_batch in batch(instance_list, batch_size):
                if as_query:
                    stmt = delete(instance_type).where(
                        instance_type.id.in_(
                            [instance.id for instance in instance_batch]
                        )
                    )
                    await session.execute(stmt)
                else:
                    for instance in instance_batch:
                        await session.delete(instance)
                    await session.flush()
