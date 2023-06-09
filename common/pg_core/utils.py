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
                await session.commit()

    return instance_list


async def bulk_delete(instance_list: List[T]) -> None:
    """
    Delete a list of instances from the database in batches.

    :param instance_list: A list of instances to be deleted from the database
    """
    batch_size = 100
    instance_type = type(instance_list[0])
    assert all(isinstance(instance, instance_type) for instance in instance_list)

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for instance_batch in batch(instance_list, batch_size):
                stmt = delete(instance_type).where(
                    instance_type.id.in_([instance.id for instance in instance_batch])
                )
                await session.execute(stmt)


async def bulk_upsert(
    table: Type[T], index_elements: list[str], instance_list: List[T]
) -> List[T]:
    """
    Add or update a list of instances to the database in batches.

    :param table: The table class corresponding to the instances
    :param instance_list: A list of instances to be added to the database
    :return: The list of instances added to the database
    """
    batch_size = 100

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for instance_batch in batch(instance_list, batch_size):
                # Convert instances to dictionaries
                dict_batch = [instance.__dict__ for instance in instance_batch]

                # Create the Insert object
                stmt = insert(table).values(dict_batch)

                # The 'on conflict do update' clause
                # Here you need to define the 'index_elements' and 'set_' arguments
                # 'index_elements' should be the list of columns that form the primary key or unique index
                # 'set_' should be a dictionary where the key is the column name and the value is the new value for that column
                # in this case we are setting it to the excluded value, which represents the value that would have been inserted
                do_update_stmt = stmt.on_conflict_do_update(
                    index_elements=index_elements,
                    set_={
                        key: getattr(stmt.excluded, key) for key in dict_batch[0].keys()
                    },
                )

                await session.execute(do_update_stmt)
                await session.commit()

    return instance_list
