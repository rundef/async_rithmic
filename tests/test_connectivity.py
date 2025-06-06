import pytest
import asyncio
import contextlib
from unittest.mock import AsyncMock, MagicMock, patch
from websockets.exceptions import ConnectionClosedError
from async_rithmic.helpers.connectivity import DisconnectionHandler, try_to_reconnect
from async_rithmic import ReconnectionSettings

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
        self.client = MagicMock()
        self.client.reconnection_settings = ReconnectionSettings(
            backoff_type="constant",
            interval=0.01,
            max_retries=20,
        )

        self._reconnect_lock = asyncio.Lock()
        self._reconnect_event = asyncio.Event()
        self._reconnect_event.set()

@pytest.mark.parametrize("fail_on_attempt", [1, 3, 5])
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


async def test_try_to_reconnect_success():
    plant = FakePlant()

    result = await try_to_reconnect(plant)
    assert result is True
    assert plant._connect.call_count == 1
    assert plant._login.call_count == 1


async def test_disconnection_handler_gives_up_after_max_retries():
    plant = FakePlant()
    plant._connect = AsyncMock(side_effect=Exception("fail_connect"))
    plant.client.reconnection_settings = ReconnectionSettings(
        backoff_type="constant",
        interval=0.01,
        max_retries=20,
    )

    async def trigger_recv():
        async with DisconnectionHandler(plant):
            raise ConnectionClosedError(rcvd=None, sent=None)
    with pytest.raises(RuntimeError, match="Unable to reconnect WebSocket"):
        # Just trigger a single disconnection -> it will fail to reconnect
        await trigger_recv()

    assert plant._connect.call_count > 0

@pytest.mark.parametrize("function_name", [
    "_recv_loop",
    "_send_and_recv",
])
async def test_no_deadlock_on_reconnect(ticker_plant_mock, function_name):
    plant = ticker_plant_mock
    plant.client.reconnection_settings = ReconnectionSettings(
        backoff_type="constant",
        interval=0.01,
        max_retries=20,
    )

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


@pytest.mark.parametrize("settings, attempt, expected_range", [
    # === CONSTANT BACKOFF ===
    (ReconnectionSettings(max_retries=5, backoff_type="constant", interval=10), 1, (10, 10)),
    (ReconnectionSettings(max_retries=5, backoff_type="constant", interval=10), 3, (10, 10)),
    (ReconnectionSettings(max_retries=5, backoff_type="constant", interval=10, jitter_range=(0.1, 0.5)), 1, (10.1, 10.5)),


    # === LINEAR BACKOFF ===
    (ReconnectionSettings(max_retries=5, backoff_type="linear", interval=10, max_delay=100), 3, (30, 30)),
    (ReconnectionSettings(max_retries=5, backoff_type="linear", interval=25, max_delay=60), 3, (60, 60)),  # capped
    (ReconnectionSettings(max_retries=5, backoff_type="linear", interval=15, max_delay=1000, jitter_range=(0.2, 1.2)), 4, (60.2, 61.2)),

    # === EXPONENTIAL BACKOFF ===
    (ReconnectionSettings(max_retries=5, backoff_type="exponential", interval=2, max_delay=100), 3, (8, 8)),
    (ReconnectionSettings(max_retries=5, backoff_type="exponential", interval=3, max_delay=100), 4, (81, 81)),
    (ReconnectionSettings(max_retries=5, backoff_type="exponential", interval=5, max_delay=100), 4, (100, 100)),  # capped: 5^4 = 625 > 100
    (ReconnectionSettings(max_retries=5, backoff_type="exponential", interval=2, max_delay=1000, jitter_range=(1, 2)), 5, (32 + 1, 32 + 2)),

])
def test_get_delay(settings, attempt, expected_range):
    delay = settings.get_delay(attempt)
    assert expected_range[0] <= delay <= expected_range[1], (
        f"Backoff delay {delay} not in expected range {expected_range} "
        f"for type={settings.backoff_type}, attempt={attempt}"
    )

async def test_send_retries_after_reconnect_success(ticker_plant_mock):
    plant = ticker_plant_mock
    plant.client.reconnection_settings = ReconnectionSettings(
        backoff_type="constant",
        interval=0.01,
        max_retries=20,
    )

    # First call to send raises, second call succeeds
    plant.ws.send = AsyncMock(side_effect=[ConnectionClosedError(rcvd=None, sent=None), None])

    # Mock try_to_reconnect to succeed
    with patch("async_rithmic.plants.base.try_to_reconnect", new=AsyncMock(return_value=True)):
        await plant._send(b"test-message")

    assert plant.ws.send.call_count == 2

async def test_only_one_reconnect():
    plant = FakePlant()

    async def _reconnect_logic(*args, **kwargs):
        await asyncio.sleep(1)
        return True

    reconnect_mock = AsyncMock(side_effect=_reconnect_logic)

    with patch("async_rithmic.helpers.connectivity._try_to_reconnect", reconnect_mock):
        await asyncio.gather(
            try_to_reconnect(plant),
            try_to_reconnect(plant),
        )

    # Assert reconnect was only attempted once
    assert reconnect_mock.call_count == 1

