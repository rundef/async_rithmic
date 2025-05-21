import asyncio
import traceback
from contextlib import asynccontextmanager

@asynccontextmanager
async def try_acquire_lock(plant, timeout: float = 5.0, context: str = ""):
    """
    Attempts to acquire an asyncio.Lock with timeout.
    Logs and raises on timeout to help detect deadlocks.
    """

    acquired = False
    try:
        await asyncio.wait_for(plant.lock.acquire(), timeout=timeout)
        acquired = True
        yield

    except asyncio.TimeoutError:
        plant.logger.error(f"[LOCK TIMEOUT] Failed to acquire lock after {timeout:.2f}s. {context}")
        plant.logger.error("Stack:\n" + "".join(traceback.format_stack()))
        raise

    finally:
        if acquired:
            plant.lock.release()

