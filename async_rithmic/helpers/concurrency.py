import asyncio
import traceback
from contextlib import asynccontextmanager

@asynccontextmanager
async def try_acquire_lock(plant, timeout: float = 10.0, context: str = "", lock=None):
    """
    Attempts to acquire an asyncio.Lock with timeout.
    Logs and raises on timeout to help detect deadlocks.

    `lock` selects which lock to take; defaults to plant.send_lock (the SEND lock).
    The recv loop / inline-recv paths pass plant.recv_lock so reads never block the
    heartbeat send, and sends never block reads.
    """

    if lock is None:
        lock = plant.send_lock

    acquired = False
    try:
        await asyncio.wait_for(lock.acquire(), timeout=timeout)

        acquired = True
        lock._current_context = context

        yield

    except asyncio.TimeoutError:
        plant.logger.error(f"[LOCK TIMEOUT] Failed to acquire lock after {timeout:.2f}s.")
        plant.logger.error(f"[WAITING CONTEXT] {context}")

        blocking_context = getattr(lock, "_current_context", None)
        if blocking_context:
            plant.logger.error(f"[BLOCKING CONTEXT] {blocking_context}")

        plant.logger.error("Stack:\n" + "".join(traceback.format_stack()))
        raise

    finally:
        if acquired:
            lock._current_context = None
            lock.release()
