from itertools import chain, islice
from typing import Iterable, List, TypeVar

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
    batch_size = 50

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for instance_batch in batch(instance_list, batch_size):
                for instance in instance_batch:
                    session.add(instance)
            await session.commit()

    return instance_list


async def bulk_delete(instance_list: List[T]) -> None:
    """
    Delete a list of instances from the database in batches.

    :param instance_list: A list of instances to be deleted from the database
    """
    batch_size = 50

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for instance_batch in batch(instance_list, batch_size):
                for instance in instance_batch:
                    await session.delete(instance)
                await session.flush()
