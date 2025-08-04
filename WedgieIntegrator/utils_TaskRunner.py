import asyncio
import time

import logging
import structlog

_logger = logging.getLogger(__name__)
log = structlog.wrap_logger(_logger)


class TaskRunner:
    is_finished: bool = False
    result = None

    def __init__(self, logger=None):
        self.__log = logger or log

    async def __aenter__(self):
        return self

    def __enter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __status_updates(self, sec_between_updates: int):
        start_time = time.time()
        last_update = time.time()
        while not self.is_finished:
            await asyncio.sleep(0.5)
            if time.time() - last_update > sec_between_updates:
                self.__log.info(f"Waiting on task to complete. Run time so far: {round(time.time() - start_time)} seconds.")
                last_update = time.time()

    async def __execute(self, func, *args, **kwargs):
        self.result = await func(*args, **kwargs)
        self.is_finished = True

    async def run_task_async(self, func, *args, sec_between_updates: int = 10, **kwargs):
        tasks = [
            self.__status_updates(sec_between_updates),
            self.__execute(func, *args, **kwargs)
        ]
        await asyncio.gather(*tasks)
        return self.result

    def run_task_sync(self, func, *args, sec_between_updates: int = 10, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.run_task_async(func, *args, sec_between_updates=sec_between_updates, **kwargs))
