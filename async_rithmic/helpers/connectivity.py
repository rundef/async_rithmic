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
    Attempts to reconnect to a plant, up to {max_retries} time
    """

    settings = plant.client.reconnection_settings

    while True:
        if settings.max_retries is not None and attempt > settings.max_retries:
            plant.logger.error("Max reconnection attempts reached. Could not reconnect.")
            return False

        wait_time = plant.client.reconnection_settings.get_delay(attempt)

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

        attempt += 1
