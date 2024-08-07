# Workarounds for asyncio in Python 3.7

import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()


# Workaround for Python 3.7 because asyncio.run was added in 3.8
def run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)
    finally:
        if not loop.is_running():
            loop.close()


# Workaround for Python 3.7 because asyncio.run was added in 3.9
async def to_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args, **kwargs)
