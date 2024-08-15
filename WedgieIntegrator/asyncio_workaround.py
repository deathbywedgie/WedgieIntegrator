# Workarounds for asyncio in Python 3.7

import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()


# Workaround for Python 3.7 because asyncio.run was added in 3.8
def run(coro):
    try:
        # Check if there's a running event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If there's a running loop, we can't use run_until_complete
            return asyncio.run_coroutine_threadsafe(coro, loop).result()

        # If the loop is not running, we can use it
        return loop.run_until_complete(coro)
    except RuntimeError:
        # Create a new event loop if none exists or if the loop is closed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        # Do not close the loop if it's running or if it was newly created in this call
        if not loop.is_running():
            loop.close()


# Workaround for Python 3.7 because asyncio.run was added in 3.9
async def to_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args, **kwargs)
