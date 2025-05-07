import pytest
import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch
from websockets.exceptions import ConnectionClosedError
from async_rithmic.helpers.connectivity import DisconnectionHandler, _try_to_reconnect

class FakePlant:
    def __init__(self):
        self.logger = MagicMock(
            info=print,
            error=print,
            exception=print,
            warning=print,
            debug=print,
        )
        self._connect = AsyncMock()
        self._login = AsyncMock()

@patch("async_rithmic.helpers.connectivity.compute_backoff", MagicMock(return_value=0.01))
@pytest.mark.parametrize("fail_on_attempt", [1, 3, 5])
@pytest.mark.asyncio
async def test_disconnection_handler_retries_and_succeeds(fail_on_attempt):
    plant = FakePlant()
    attempt = 0

    async def unstable_recv():
        nonlocal attempt
        attempt += 1
        if attempt <= fail_on_attempt:
            raise ConnectionClosedError(rcvd=None, sent=None)
        return b"OK"

    # Retry loop to re-enter DisconnectionHandler after reconnect
    for _ in range(10):  # avoid infinite loop
        try:
            async with DisconnectionHandler(plant):
                result = await unstable_recv()
                break
        except ConnectionClosedError:
            continue
    else:
        raise AssertionError("Unstable recv never succeeded")

    assert result == b"OK"
    assert attempt == fail_on_attempt + 1
    assert plant._connect.call_count == fail_on_attempt


@patch("async_rithmic.helpers.connectivity.compute_backoff", MagicMock(return_value=0.01))
async def test_try_to_reconnect_success():
    plant = FakePlant()

    result = await _try_to_reconnect(plant, max_retries=3)
    assert result is True
    assert plant._connect.call_count == 1
    assert plant._login.call_count == 1

@patch("async_rithmic.helpers.connectivity.compute_backoff", MagicMock(return_value=0.01))
async def test_disconnection_handler_gives_up_after_max_retries():
    plant = FakePlant()
    plant._connect = AsyncMock(side_effect=Exception("fail_connect"))

    async def trigger_recv():
        async with DisconnectionHandler(plant):
            raise ConnectionClosedError(rcvd=None, sent=None)
    with pytest.raises(RuntimeError, match="Unable to reconnect WebSocket"):
        # Just trigger a single disconnection -> it will fail to reconnect
        await trigger_recv()

    assert plant._connect.call_count > 0

@patch("async_rithmic.helpers.connectivity.compute_backoff", MagicMock(return_value=0.01))
@pytest.mark.parametrize("function_name", [
    "_listen",
    "_send_and_recv",
])
async def test_no_deadlock_on_reconnect(ticker_plant_mock, function_name):
    plant = ticker_plant_mock

    plant._recv = AsyncMock()
    plant.heartbeat_interval = None
    call_counter = 0

    async def recv_mock_fn():
        nonlocal call_counter
        call_counter += 1
        if call_counter <= 5:
            raise ConnectionClosedError(rcvd=None, sent=None)
        await asyncio.sleep(10)  # simulate blocking

    plant._recv.side_effect = recv_mock_fn


    async def fake_connect():
        # Simulate reconnect path that also acquires the lock
        async with plant.lock:
            await asyncio.sleep(0.1)

    plant._connect = fake_connect
    plant._login = AsyncMock()
    plant._send_request = AsyncMock()

    # Start the infinite listener
    fn = getattr(plant, function_name)
    listener_task = asyncio.create_task(fn())

    await asyncio.sleep(0.3)

    assert plant._recv.call_count >= 2, "Listener is likely deadlocked: _recv not called after reconnect"

    listener_task.cancel()
    with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
        await listener_task
