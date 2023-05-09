from common.config.globals import ASYNC_PG_SESSION


def batch(iterable, size):
    from itertools import chain, islice

    iterator = iter(iterable)
    for first in iterator:
        yield list(chain([first], islice(iterator, size - 1)))


async def bulk_add(instance_list: list) -> list:
    batch_size = 50
    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for instance_batch in batch(instance_list, batch_size):
                for instance in instance_batch:
                    session.add(instance)
            await session.commit()

    return instance_list


async def bulk_delete(instance_list: list):
    batch_size = 50

    async with ASYNC_PG_SESSION() as session:
        async with session.begin():
            for instance_batch in batch(instance_list, batch_size):
                for instance in instance_batch:
                    await session.delete(instance)
                await session.flush()
