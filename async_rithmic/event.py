import asyncio

from .logger import logger

class Event:
    def __init__(self):
        self._subscribers = []

    def __iadd__(self, callback):
        self._subscribers.append(callback)
        return self

    def __isub__(self, callback):
        self._subscribers.remove(callback)
        return self

    async def notify(self, *args, **kwargs):
        for callback in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(*args, **kwargs)
                else:
                    callback(*args, **kwargs)
            except:
                logger.exception("Error in callback function")
