import asyncio
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

        if not await try_to_reconnect(plant):
            plant.logger.error("Failed to reconnect - giving up")
            raise RuntimeError("Unable to reconnect WebSocket") from e

async def try_to_reconnect(plant, attempt=1):
    """
    A wrapper around the reconnection logic that ensures no simultaneous reconnection attempts.
    """

    async with plant._reconnect_lock:
        if not plant._reconnect_event.is_set():
            plant.logger.info("Reconnection already in progress, waiting...")
            await plant._reconnect_event.wait()
            return True

        plant._reconnect_event.clear()

    try:
        return await _try_to_reconnect(plant, attempt)
    finally:
        plant._reconnect_event.set()

async def _try_to_reconnect(plant, attempt):
    """
    Attempts to reconnect to a plant
    """

    settings = plant.client.reconnection_settings

    while True:
        plant.logger.info(f"Reconnection attempt #{attempt}")

        if settings.max_retries is not None and attempt > settings.max_retries:
            plant.logger.error("Max reconnection attempts reached. Could not reconnect.")
            return False

        try:
            await asyncio.wait_for(plant._connect(), timeout=5)
            await asyncio.wait_for(plant._login(), timeout=5)

            plant.logger.info("Reconnection successful.")
            return True

        except asyncio.TimeoutError:
            plant.logger.warning("Reconnection attempt timed out. Retrying ...")

        except Exception as e:
            plant.logger.warning(f"Reconnection failed: {e}. Retrying...")

        attempt += 1

        wait_time = plant.client.reconnection_settings.get_delay(attempt)
        plant.logger.info(f"Waiting {wait_time} seconds before the next reconnection attempt ...")
        await asyncio.sleep(wait_time)

    return False
