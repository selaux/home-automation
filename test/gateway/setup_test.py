import sys
import asyncio
from os import path

def setup():
    gateway_path = path.realpath(path.abspath(path.join(__file__, '../../../gateway/')))
    if not gateway_path in sys.path:
        sys.path.append(gateway_path)

def async_test(function):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(function)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
    return wrapper
