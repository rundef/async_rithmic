"""Regression test: order-path terminal response must not be dropped.

Reproduces the concurrent submit_order bug: when an order-path request (submit
312/modify 314/cancel 316/bracket 330) gets its acknowledgement as a *terminal*
response (rp_code=='0') — which is the only frame that arrives under concurrent
load on a single Rithmic session — `_process_response` jumped straight to
`mark_complete` without first calling `handle_response`, unless the template_id
was in the allow-list `_terminal_carries_data`. The order-ack templates
(313/315/317/331) were NOT in that set, so the ack was discarded and
`send_and_collect` returned an empty list -> the caller raised "Rithmic empty
response".

Unlike a single-order test (which gets a data frame + a terminal, so the data
frame is stored regardless), this drives the *terminal-only* case that occurs
under concurrency — which is why it reproduces while single-order tests don't.

These exercise the REAL `BasePlant._process_response` + `RequestManager` against
a real `OrderPlant` and real protobuf responses — no live connection, no
application code. Fails on the old allow-list `{11, 15, 114, 301}`; passes with
`{11, 15, 114, 301, 313, 315, 317, 331}`.
"""
import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest

from async_rithmic import protocol_buffers as pb
from async_rithmic.plants.order import OrderPlant


def _terminal_ack(request_id, template_id=313):
    """A real protobuf order-ack as a terminal-only response (rp_code='0')."""
    resp = pb.response_new_order_pb2.ResponseNewOrder()
    resp.template_id = template_id
    resp.user_msg.append(request_id)
    resp.rp_code.append('0')          # terminal success marker, no data frame preceded it
    return resp


@pytest.fixture
def order_plant():
    # A MagicMock client is enough — __init__ only wires event handlers + logger.
    return OrderPlant(MagicMock())


@pytest.mark.asyncio
async def test_terminal_only_order_ack_is_stored(order_plant):
    rid = "req-single"
    order_plant.request_manager.start(
        rid, request={"template_id": 312}, expected_response={"user_msg": [rid]}
    )

    await order_plant._process_response(_terminal_ack(rid))

    stored = order_plant.request_manager.responses.get(rid, [])
    assert stored, (
        "terminal-only order ack (313, rp_code=0) was dropped before mark_complete; "
        "send_and_collect would return [] -> 'Rithmic empty response'"
    )
    assert stored[0].template_id == 313


@pytest.mark.asyncio
async def test_concurrent_terminal_only_acks_all_stored(order_plant):
    # Mirrors live_propfirms 2026-04-23: N accounts submit on one session; each
    # request gets only its terminal ack (data frames lost in the race).
    rids = [f"req-{i}" for i in range(6)]
    for rid in rids:
        order_plant.request_manager.start(
            rid, request={"template_id": 312}, expected_response={"user_msg": [rid]}
        )

    await asyncio.gather(*(order_plant._process_response(_terminal_ack(rid)) for rid in rids))

    dropped = [rid for rid in rids if not order_plant.request_manager.responses.get(rid)]
    assert not dropped, f"order acks dropped for {dropped} -> empty response -> missed entries"


@pytest.mark.asyncio
async def test_genuine_absence_still_times_out(order_plant):
    # The fix must not mask a real no-response: if nothing arrives, time out.
    order_plant._send_request = AsyncMock()
    with pytest.raises(asyncio.TimeoutError):
        await order_plant.request_manager.send_and_collect(
            timeout=0.2, user_msg="req-none", template_id=312, expected_response={}
        )
