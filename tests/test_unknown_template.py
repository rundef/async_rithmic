import asyncio
import logging
from contextlib import suppress
from unittest.mock import AsyncMock

from pattern_kit import Event

from async_rithmic import protocol_buffers as pb
from conftest import _convert_proto_message_to_bytes


def _base_buffer(template_id):
    """Build a length-prefixed buffer carrying only a template id."""
    message = pb.base_pb2.Base()
    message.template_id = template_id
    return _convert_proto_message_to_bytes(message)


def test_unknown_template_id_returns_none_and_warns_once(order_plant_mock, caplog):
    """
    An unmapped template id must not raise (which used to flood the logs with a
    full traceback for every such message). It returns None and logs a single
    warning per template id.
    """
    buffer = _base_buffer(9999)

    with caplog.at_level(logging.WARNING):
        first = order_plant_mock._convert_bytes_to_response(buffer)
        second = order_plant_mock._convert_bytes_to_response(buffer)

    assert first is None
    assert second is None
    assert order_plant_mock._warned_unknown_template_ids == {9999}

    warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "9999" in r.getMessage()
    ]
    assert len(warnings) == 1


async def test_process_loop_drops_unknown_and_keeps_going(order_plant_mock):
    """
    The processing loop must silently drop an unmapped message and continue
    dispatching the messages that follow it.
    """
    plant = order_plant_mock
    plant._process_response = AsyncMock()

    unknown = _base_buffer(9999)

    known_msg = pb.response_heartbeat_pb2.ResponseHeartbeat()
    known_msg.template_id = 19
    known = _convert_proto_message_to_bytes(known_msg)

    await plant._inbound_queue.put(unknown)
    await plant._inbound_queue.put(known)

    task = asyncio.create_task(plant._process_loop())
    await asyncio.sleep(0.05)
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

    # Only the known message reached _process_response; the unknown one was dropped
    assert plant._process_response.await_count == 1
    assert plant._process_response.await_args.args[0].template_id == 19


async def test_account_rms_update_decodes_and_fires_event(order_plant_mock):
    """
    A template id 358 frame decodes to AccountRmsUpdates and is dispatched to
    the on_account_rms_update callback.
    """
    plant = order_plant_mock

    received = []

    async def callback(message):
        received.append(message)

    plant.client.on_account_rms_update = Event()
    plant.client.on_account_rms_update += callback

    msg = pb.account_rms_updates_pb2.AccountRmsUpdates()
    msg.template_id = 358
    msg.account_id = "TEST_ACCT"
    buffer = _convert_proto_message_to_bytes(msg)

    response = plant._convert_bytes_to_response(buffer)
    assert isinstance(response, pb.account_rms_updates_pb2.AccountRmsUpdates)
    assert response.template_id == 358

    await plant._process_response(response)

    assert len(received) == 1
    assert received[0].account_id == "TEST_ACCT"
