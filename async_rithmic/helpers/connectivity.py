import asyncio
import random
from contextlib import asynccontextmanager
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

@asynccontextmanager
async def DisconnectionHandler(plant):
    """
    Automatically attempts to reconnect the WebSocket on ConnectionClosed* errors.
    """
    try:
        yield

    except (ConnectionClosedError, ConnectionClosedOK) as e:
        plant.logger.warning("WebSocket connection closed unexpectedly")

        if not await _try_to_reconnect(plant):
            plant.logger.error("Failed to reconnect - giving up")
            raise RuntimeError("Unable to reconnect WebSocket") from e

async def _try_to_reconnect(plant, max_retries=20, attempt=1):
    """
    Attempts to reconnect to a plant, up to {max_retries} time
    """

    wait_time = compute_backoff(attempt=attempt)

    plant.logger.info(f"Reconnection attempt #{attempt} in {wait_time} seconds...")
    await asyncio.sleep(wait_time)

    try:
        await asyncio.wait_for(plant._connect(), timeout=10)
        await asyncio.wait_for(plant._login(), timeout=10)

        plant.logger.info("Reconnection successful.")
        return True

    except asyncio.TimeoutError:
        plant.logger.warning("Reconnection attempt timed out. Retrying ...")

    except Exception as e:
        plant.logger.warning(f"Reconnection failed: {e}. Retrying...")

    if attempt < max_retries:
        return await _try_to_reconnect(plant, max_retries, attempt + 1)

    plant.logger.error("Max reconnection attempts reached. Could not reconnect.")
    return False

def compute_backoff(base=2, attempt=1, max_value=120, jitter_range=(0, 1.5)):
    """
    Computes exponential backoff with jitter.
    """
    base_delay = min(base ** attempt, max_value)
    jitter = random.uniform(*jitter_range)
    return base_delay + jitter
