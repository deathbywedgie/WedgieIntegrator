# Workarounds for asyncio in Python 3.7

import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()


# Workaround for Python 3.7 because asyncio.to_thread was added in 3.9
async def to_thread(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, func, *args, **kwargs)
