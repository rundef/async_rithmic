import pytest
import asyncio
import contextlib
import io
import logging
from unittest.mock import AsyncMock, MagicMock
from websockets.exceptions import ConnectionClosedError
from websockets.protocol import OPEN
from pattern_kit import Event

from async_rithmic import ReconnectionSettings, RithmicClient
from async_rithmic.enums import SysInfraType


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


async def test_recv_loop_exits_on_disconnect(ticker_plant_mock):
    plant = ticker_plant_mock
    plant._recv = AsyncMock(side_effect=ConnectionClosedError(rcvd=None, sent=None))

    task = asyncio.create_task(plant._recv_loop())
    await asyncio.sleep(0.1)

    assert task.done(), "recv_loop should exit after a disconnect"
    assert plant._disconnect_event.is_set(), "_disconnect_event should be set on disconnect"

    with contextlib.suppress(asyncio.CancelledError):
        await task


async def test_reconnect_loop_restarts_and_calls_login(ticker_plant_mock):
    plant = ticker_plant_mock
    plant.client.reconnection_settings = ReconnectionSettings(
        backoff_type="constant",
        interval=0.01,
        max_retries=5,
    )
    plant._connect = AsyncMock()
    plant._login = AsyncMock()
    plant._start_io_tasks = AsyncMock()
    plant._stop_io_tasks = AsyncMock()

    task = asyncio.create_task(plant._reconnect_loop())

    plant._disconnect_event.set()
    await asyncio.sleep(0.2)

    assert plant._stop_io_tasks.call_count == 1
    assert plant._connect.call_count == 1
    assert plant._start_io_tasks.call_count == 1
    assert plant._login.call_count == 1
    assert plant._reconnected_event.is_set()

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


async def test_send_retries_after_reconnect_success(ticker_plant_mock):
    plant = ticker_plant_mock
    client = MagicMock()
    client.on_unexpected_disconnected = Event()
    observed = []
    client.on_unexpected_disconnected += (
        lambda plant_type: observed.append(plant_type)
    )
    client._signal_unexpected_disconnect = RithmicClient._signal_unexpected_disconnect.__get__(
        client
    )
    plant.client = client
    plant.client.reconnection_settings = ReconnectionSettings(
        backoff_type="constant",
        interval=0.01,
        max_retries=20,
    )

    ws = MagicMock()
    ws.state = OPEN
    ws.send = AsyncMock(side_effect=[ConnectionClosedError(rcvd=None, sent=None), None])
    plant.ws = ws

    async def simulate_reconnect():
        await asyncio.sleep(0.05)
        plant._reconnected_event.set()

    asyncio.create_task(simulate_reconnect())
    await plant._send(b"test-message")

    assert plant.ws.send.call_count == 2
    assert observed == [plant.plant_type]


async def test_unexpected_disconnect_handler_observes_receive_loop_loss(ticker_plant_mock):
    client = MagicMock()
    client.on_unexpected_disconnected = Event()
    observed = []

    async def on_unexpected_disconnected(plant_type):
        observed.append(plant_type)

    client.on_unexpected_disconnected += on_unexpected_disconnected

    client._signal_unexpected_disconnect = RithmicClient._signal_unexpected_disconnect.__get__(client)
    plant = ticker_plant_mock
    plant.client = client
    plant._recv = AsyncMock(side_effect=ConnectionClosedError(rcvd=None, sent=None))

    task = asyncio.create_task(plant._recv_loop())
    await task
    assert observed == [plant.plant_type]


async def test_explicit_disconnect_does_not_invoke_unexpected_hook(ticker_plant_mock):
    client = MagicMock()
    client.on_disconnected = Event()
    client.on_unexpected_disconnected = Event()
    disconnected = []
    unexpected = []
    client.on_disconnected += lambda plant_type: disconnected.append(plant_type)
    client.on_unexpected_disconnected += (
        lambda plant_type: unexpected.append(plant_type)
    )
    plant = ticker_plant_mock
    plant.client = client
    plant.ws.state = OPEN
    plant.ws.close = AsyncMock()

    await plant._disconnect()

    assert disconnected == [plant.plant_type]
    assert unexpected == []


async def test_unexpected_disconnect_callback_failure_does_not_break_receive_cleanup(
    ticker_plant_mock,
):
    client = MagicMock()
    client.on_unexpected_disconnected = Event()

    async def failing_callback(plant_type):
        raise RuntimeError("callback failed")

    client.on_unexpected_disconnected += failing_callback
    client._signal_unexpected_disconnect = RithmicClient._signal_unexpected_disconnect.__get__(client)
    plant = ticker_plant_mock
    plant.client = client
    plant._recv = AsyncMock(side_effect=ConnectionClosedError(rcvd=None, sent=None))

    await plant._recv_loop()

    assert plant._disconnect_event.is_set()
