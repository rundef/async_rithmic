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
from async_rithmic import protocol_buffers as pb
from async_rithmic.enums import SysInfraType
from async_rithmic.exceptions import RithmicConnectionLostError
from conftest import _convert_proto_message_to_bytes, make_client, use_local_gateway


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


async def test_recv_loop_notifies_disconnected_listeners(ticker_plant_mock):
    plant = ticker_plant_mock
    disconnected = []

    async def on_disconnected(plant_type):
        disconnected.append(plant_type)

    plant.client.on_disconnected += on_disconnected
    plant._recv = AsyncMock(side_effect=ConnectionClosedError(rcvd=None, sent=None))

    await plant._recv_loop()

    assert disconnected == [plant.plant_type]


async def test_connection_loss_fails_pending_requests(ticker_plant_mock):
    plant = ticker_plant_mock
    manager = plant.request_manager
    awaiting_response = asyncio.create_task(plant.get_reference_data("ESZ6", "CME"))
    while plant.ws.send.await_count < 1:
        await asyncio.sleep(0)
    # This send hits the closed socket and waits for a reconnection
    plant.ws.send.side_effect = ConnectionClosedError(rcvd=None, sent=None)
    awaiting_reconnection = asyncio.create_task(plant.get_reference_data("NQZ6", "CME"))
    while plant.ws.send.await_count < 2:
        await asyncio.sleep(0)

    plant._recv = AsyncMock(side_effect=ConnectionClosedError(rcvd=None, sent=None))
    await plant._recv_loop()

    # Well before the 3 s request timeout.
    with pytest.raises(RithmicConnectionLostError):
        await asyncio.wait_for(awaiting_response, timeout=0.5)

    # The reconnection gives up
    plant._reconnected_event.set()
    with pytest.raises(RithmicConnectionLostError):
        await asyncio.wait_for(awaiting_reconnection, timeout=0.5)

    assert not manager.requests
    assert not manager.responses
    assert not manager.errors
    assert not manager.done_events


async def test_forced_logout_ends_the_session_without_reconnecting(rithmic_server):
    client = make_client(
        # Unlimited retries, as by default, without the default delay.
        reconnection_settings=ReconnectionSettings(backoff_type="constant", interval=0.01),
    )
    plant = client.plants["order"]
    use_local_gateway(plant, rithmic_server)
    logins = asyncio.Semaphore(0)
    plant._login = AsyncMock(side_effect=logins.release)
    forced_logouts = []
    unexpected_disconnects = []
    client.on_forced_logout += forced_logouts.append
    client.on_unexpected_disconnected += unexpected_disconnects.append

    await client.connect(plants=[SysInfraType.ORDER_PLANT], plant_connect_delay=0)
    gateway = await rithmic_server.connections.get()
    request = asyncio.create_task(plant.list_accounts())
    await gateway.recv()
    await gateway.send(_convert_proto_message_to_bytes(pb.forced_logout_pb2.ForcedLogout(template_id=77)))

    with pytest.raises(RithmicConnectionLostError, match="ForcedLogout"):
        await asyncio.wait_for(request, timeout=1)
    # Room for reconnection attempts, which must not happen.
    await asyncio.sleep(0.2)

    assert forced_logouts == ["order"]
    assert unexpected_disconnects == ["order"]
    assert not plant.is_connected
    assert rithmic_server.connections.empty()
    assert all(task.done() for task in plant._bg_tasks)

    # An explicit connect starts a new session, which reconnects automatically again.
    await client.connect(plants=[SysInfraType.ORDER_PLANT], plant_connect_delay=0)
    assert plant.is_connected
    await (await rithmic_server.connections.get()).close()
    for _ in range(3):
        await asyncio.wait_for(logins.acquire(), timeout=1)

    await client.disconnect()


async def test_forced_logout_queued_behind_a_slow_callback_still_prevents_reconnection(rithmic_server):
    client = make_client(
        reconnection_settings=ReconnectionSettings(backoff_type="constant", interval=0.01),
    )
    plant = client.plants["order"]
    use_local_gateway(plant, rithmic_server)
    plant._login = AsyncMock()
    forced_logouts = []
    client.on_forced_logout += forced_logouts.append

    async def slow_callback(notification):
        await asyncio.sleep(0.2)

    client.on_exchange_order_notification += slow_callback
    await client.connect(plants=[SysInfraType.ORDER_PLANT], plant_connect_delay=0)
    gateway = await rithmic_server.connections.get()

    # The server closes the socket right after the ForcedLogout, while the notification is processed
    notification = pb.exchange_order_notification_pb2.ExchangeOrderNotification(template_id=352)
    await gateway.send(_convert_proto_message_to_bytes(notification))
    await gateway.send(_convert_proto_message_to_bytes(pb.forced_logout_pb2.ForcedLogout(template_id=77)))
    await gateway.close()
    await asyncio.sleep(0.5)

    assert forced_logouts == ["order"]
    assert not plant.is_connected
    assert rithmic_server.connections.empty()


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


async def test_send_sees_a_reconnect_outcome_reached_while_listeners_run(ticker_plant_mock):
    plant = ticker_plant_mock
    client = MagicMock()
    client.on_unexpected_disconnected = Event()
    client._signal_unexpected_disconnect = RithmicClient._signal_unexpected_disconnect.__get__(client)
    # Gives up at once
    client.reconnection_settings = ReconnectionSettings(max_retries=0, backoff_type="constant", interval=0)

    async def slow_listener(plant_type):
        await asyncio.sleep(0.1)

    client.on_unexpected_disconnected += slow_listener
    plant.client = client
    plant._stop_io_tasks = AsyncMock()
    plant.ws.send.side_effect = ConnectionClosedError(rcvd=None, sent=None)
    reconnect_loop = asyncio.create_task(plant._reconnect_loop())

    # Instead of waiting 60 s for an outcome already reached
    with pytest.raises(RuntimeError, match="Unable to reconnect"):
        await asyncio.wait_for(plant._send(b"test-message"), timeout=1)
    assert reconnect_loop.done()


async def test_unexpected_disconnect_handler_observes_receive_loop_loss(ticker_plant_mock):
    client = MagicMock()
    client.on_disconnected = Event()
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
    client.on_disconnected = Event()
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
