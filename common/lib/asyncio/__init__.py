import asyncio
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from typing import List

from asgiref.sync import sync_to_async


async def aio_wrapper(fnc, *args, **kwargs):
    thread_sensitive = kwargs.pop("thread_sensitive", False)
    return await sync_to_async(fnc, thread_sensitive=thread_sensitive)(*args, **kwargs)


async def bound_fetch(sem, fn, args, kwargs):
    # Getter function with semaphore.
    async with sem:
        return {
            "fn": fn,
            "args": args,
            "kwargs": kwargs,
            "result": await fn(*args, **kwargs),
        }


async def bound_fetch_sync(sem, fn, args, kwargs):
    # Getter function with semaphore.
    async with sem:
        return {
            "fn": fn,
            "args": args,
            "kwargs": kwargs,
            "result": await sync_to_async(fn, thread_sensitive=False)(*args, **kwargs),
        }


async def run_in_parallel(task_list: List, threads=os.cpu_count(), sync=True):
    async def run():
        sem = asyncio.Semaphore(threads)
        futures = []
        for task in task_list:
            if sync:
                futures.append(
                    asyncio.ensure_future(
                        bound_fetch_sync(
                            sem,
                            task.get("fn"),
                            task.get("args", ()),
                            task.get("kwargs", {}),
                        )
                    )
                )
            else:
                futures.append(
                    asyncio.ensure_future(
                        bound_fetch(
                            sem,
                            task.get("fn"),
                            task.get("args", ()),
                            task.get("kwargs", {}),
                        )
                    )
                )
        responses = asyncio.gather(*futures)
        return await responses

    return await run()


def run_io_tasks_in_parallel(tasks):
    results = []
    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        running_tasks = [executor.submit(task) for task in tasks]
        for running_task in running_tasks:
            result = running_task.result()
            results.append(result)
    return results


def run_cpu_tasks_in_parallel(tasks):
    results = {}
    with ProcessPoolExecutor() as executor:
        running_tasks = [executor.submit(task) for task in tasks]
        for running_task in running_tasks:
            result = running_task.result()
            results[running_task] = result
    return results


class NoqSemaphore:
    def __init__(
        self, callback_function: any, batch_size: int, callback_is_async: bool = True
    ):
        """Makes a reusable semaphore that wraps a provided function.
        Useful for batch processing things that could be rate limited.

        Example prints hello there 3 times in quick succession, waits 3 seconds then processes another 3:
            from datetime import datetime

            async def hello_there():
                print(f"Hello there - {datetime.utcnow()}")
                await asyncio.sleep(3)

            hello_there_semaphore = NoqSemaphore(hello_there, 3)
            asyncio.run(hello_there_semaphore.process([{} for _ in range(10)]))
        """
        self.limit = asyncio.Semaphore(batch_size)
        self.callback_function = callback_function
        self.callback_is_async = callback_is_async

    async def handle_message(self, **kwargs):
        async with self.limit:
            if self.callback_is_async:
                return await self.callback_function(**kwargs)

            return await aio_wrapper(self.callback_function, **kwargs)

    async def process(self, messages: list[dict]):
        return await asyncio.gather(
            *[asyncio.create_task(self.handle_message(**msg)) for msg in messages]
        )
