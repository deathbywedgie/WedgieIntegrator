# Workaround for Python 3.7 because asyncio.run and asyncio.to_thread were added in 3.8

from asyncio import get_event_loop
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()


async def to_thread(func, *args, **kwargs):
    loop = get_event_loop()
    return await loop.run_in_executor(executor, func, *args, **kwargs)


# Workaround for Python 3.7 because asyncio.run was added in 3.8
def run(coro):
    loop = get_event_loop()
    result = loop.run_until_complete(coro)
    loop.close()
    return result
