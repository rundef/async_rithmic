import asyncio
from google.protobuf.json_format import MessageToDict
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK


class BackgroundTaskMixin:
    """
    Mixin that manages background task orchestration for a plant.

    Starts:
    - A recv loop for receiving raw messages
    - A process loop for decoding and dispatching responses
    - A heartbeat loop for regular keep-alives
    - A reconnect loop that owns the full reconnect lifecycle
    """

    def __init__(self, **kwargs):
        self._inbound_queue = asyncio.Queue()
        self._bg_tasks: list[asyncio.Task] = []

    async def _start_io_tasks(self):
        self._bg_tasks.append(asyncio.create_task(self._recv_loop(), name="recv_loop"))
        self._bg_tasks.append(asyncio.create_task(self._process_loop(), name="process_loop"))
        self._bg_tasks.append(asyncio.create_task(self._heartbeat_loop(), name="heartbeat_loop"))

    async def _stop_io_tasks(self):
        io_tasks = [t for t in self._bg_tasks if t.get_name() in {"recv_loop", "process_loop", "heartbeat_loop"}]
        for task in io_tasks:
            task.cancel()
        await asyncio.gather(*io_tasks, return_exceptions=True)
        for task in io_tasks:
            self._bg_tasks.remove(task)

    async def _start_background_tasks(self):
        await self._start_io_tasks()
        self._bg_tasks.append(asyncio.create_task(self._reconnect_loop(), name="reconnect_loop"))
        self.logger.debug("Background tasks started")

    async def _stop_background_tasks(self):
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
        Exits cleanly on disconnect; _reconnect_loop takes over from there.
        """
        while True:
            try:
                buffer = None
                try:
                    buffer = await asyncio.wait_for(self._recv(), timeout=self.listen_interval)
                except asyncio.TimeoutError:
                    pass

                if buffer is not None:
                    await self._inbound_queue.put(buffer)

            except (ConnectionClosedError, ConnectionClosedOK):
                self.logger.warning("WebSocket connection closed — signalling reconnect")
                self._disconnect_event.set()
                return

            except asyncio.CancelledError:
                return

            except Exception:
                self.logger.exception("Exception in background listener")

    async def _reconnect_loop(self):
        """
        Waits for a disconnect signal, then owns the full reconnect lifecycle:
        stop IO tasks → retry _connect → start IO tasks → _login.
        By starting IO tasks (including _recv_loop) before calling _login, the login
        flow can safely use the request manager instead of _send_and_recv_immediate.
        """
        while True:
            try:
                await self._disconnect_event.wait()
                self._disconnect_event.clear()
                self._reconnected_event.clear()

                self.logger.warning("Connection lost - attempting to reconnect")
                await self._stop_io_tasks()

                settings = self.client.reconnection_settings
                attempt = 1
                connected = False

                while True:
                    wait_time = settings.get_delay(attempt)
                    self.logger.info(f"Waiting {wait_time:.1f}s before reconnect attempt #{attempt}")
                    await asyncio.sleep(wait_time)

                    self.logger.info(f"Reconnection attempt #{attempt}")

                    if settings.max_retries is not None and attempt > settings.max_retries:
                        self.logger.error("Max reconnection attempts reached. Giving up.")
                        break

                    try:
                        await asyncio.wait_for(self._connect(), timeout=5)
                        connected = True
                        break
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Reconnect attempt #{attempt} timed out")
                    except Exception as e:
                        self.logger.warning(f"Reconnect attempt #{attempt} failed: {e}")

                    attempt += 1

                if not connected:
                    self._reconnected_event.set()
                    return

                await self._start_io_tasks()

                try:
                    await asyncio.wait_for(self._login(), timeout=30)
                except Exception as e:
                    self.logger.error(f"Login failed after reconnect: {e}. Will retry.")
                    self._disconnect_event.set()
                    self._reconnected_event.set()
                    continue

                self._reconnected_event.set()
                self.logger.info("Reconnection successful.")

            except asyncio.CancelledError:
                return

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
