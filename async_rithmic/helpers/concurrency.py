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
        plant.lock._current_context = context

        yield

    except asyncio.TimeoutError:
        plant.logger.error(f"[LOCK TIMEOUT] Failed to acquire lock after {timeout:.2f}s.")
        plant.logger.error(f"[WAITING CONTEXT] {context}")

        blocking_context = getattr(plant.lock, "_current_context", None)
        if blocking_context:
            plant.logger.error(f"[BLOCKING CONTEXT] {blocking_context}")

        plant.logger.error("Stack:\n" + "".join(traceback.format_stack()))
        raise

    finally:
        if acquired:
            plant.lock._current_context = None
            plant.lock.release()
