import asyncio
from google.protobuf.json_format import MessageToDict

from .connectivity import DisconnectionHandler
from .concurrency import try_acquire_lock

class BackgroundTaskMixin:
    """
    Mixin that manages background task orchestration for a plant.

    Starts:
    - A recv loop for receiving raw messages
    - A process loop for decoding and dispatching responses
    - A heartbeat loop for regular keep-alives
    """

    def __init__(self, **kwargs):
        self._inbound_queue = asyncio.Queue()
        self._bg_tasks: list[asyncio.Task] = []

    async def _start_background_tasks(self):
        """
        Starts background tasks and stores their references for graceful shutdown.
        """
        self._bg_tasks.append(asyncio.create_task(self._recv_loop(), name="recv_loop"))
        self._bg_tasks.append(asyncio.create_task(self._process_loop(), name="process_loop"))
        self._bg_tasks.append(asyncio.create_task(self._heartbeat_loop(), name="heartbeat_loop"))

        self.logger.debug("Background tasks started")

    async def _stop_background_tasks(self):
        """
        Cancels and awaits all background tasks.
        """
        if not self._bg_tasks:
            return

        for task in self._bg_tasks:
            task.cancel()

        results = await asyncio.gather(*self._bg_tasks, return_exceptions=True)

        for task, result in zip(self._bg_tasks, results):
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                self.logger.warning(f"Background task {task.get_name()} failed: {result}")

        self._bg_tasks.clear()
        self.logger.debug("Background tasks stopped")

    async def _recv_loop(self):
        """
        Continuously reads from the WebSocket and pushes raw messages to the inbound queue.
        """

        while True:
            try:
                async with DisconnectionHandler(self):
                    buffer = None

                    async with try_acquire_lock(self, context="_recv_loop"):
                        try:
                            buffer = await asyncio.wait_for(self._recv(), timeout=self.listen_interval)
                        except asyncio.TimeoutError:
                            pass

                    if buffer is not None:
                        await self._inbound_queue.put(buffer)

            except asyncio.TimeoutError:
                pass

            except asyncio.CancelledError:
                break

            except:
                self.logger.exception("Exception in background listener")

    async def _process_loop(self):
        """
        Consumes raw messages from the inbound queue and processes them.
        """
        while True:
            buffer = await self._inbound_queue.get()
            try:
                response = self._convert_bytes_to_response(buffer)
                self.logger.debug(f"Received message {MessageToDict(response)}")

                await self._process_response(response)

            except asyncio.CancelledError:
                break

            except Exception as e:
                self.logger.exception("Error processing response", exc_info=e)

    async def _heartbeat_loop(self):
        """
        Periodically sends heartbeats based on the negotiated interval.
        """
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval - 1)
                await self._send_heartbeat()

            except asyncio.CancelledError:
                break

            except Exception as e:
                self.logger.warning("Heartbeat failed", exc_info=e)

