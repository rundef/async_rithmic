import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from pattern_kit import Event

import pytest

from async_rithmic.plants import HistoryPlant
from async_rithmic.enums import TimeBarType


@pytest.fixture
def history_plant_mock():
    client = MagicMock()
    client.retry_settings = MagicMock(max_retries=1, timeout=3, jitter_range=None)
    client.on_historical_time_bar = Event()
    client.on_historical_tick = Event()

    plant = HistoryPlant(client)
    plant.ws = AsyncMock()
    # Stub the send to avoid real network
    plant._send_request = AsyncMock(return_value=None)

    return plant


async def test_empty_response_returns_empty_list(history_plant_mock):
    """
    Bug A: When Rithmic returns only the is_last_bar marker (no data bars),
    the code used to raise KeyError on .pop(key). Now it returns [].
    """
    plant = history_plant_mock
    key = f"MNQM6_CME_{int(TimeBarType.MINUTE_BAR)}_1"

    # Simulate the is_last_bar marker arriving right after the request is sent
    async def trigger_empty_response():
        await asyncio.sleep(0.01)
        await plant._process_response(
            MagicMock(
                template_id=203,
                rp_code=['0'],
                user_msg=[key]
            )
        )

    asyncio.create_task(trigger_empty_response())

    result = await plant.get_historical_time_bars(
        symbol="MNQM6",
        exchange="CME",
        start_time=datetime(2026, 4, 13, 0, 0),
        end_time=datetime(2026, 4, 13, 0, 1),
        bar_type=TimeBarType.MINUTE_BAR,
        bar_type_periods=1,
    )
    assert result == []
    # Events dict is cleaned up
    assert key not in plant.historical_time_bar_requests


async def test_empty_tick_response_returns_empty_list(history_plant_mock):
    """Same as Bug A but for tick data."""
    plant = history_plant_mock
    key = f"MNQM6_CME"

    # Simulate the is_last_bar marker arriving right after the request is sent
    async def trigger_empty_response():
        await asyncio.sleep(0.01)
        await plant._process_response(
            MagicMock(
                template_id=207,
                rp_code=['0'],
                user_msg=[key]
            )
        )

    asyncio.create_task(trigger_empty_response())

    result = await plant.get_historical_tick_data(
        symbol="MNQM6", exchange="CME",
        start_time=datetime(2026, 4, 13, 0), end_time=datetime(2026, 4, 13, 0, 1),
    )
    assert result == []
    # Events dict is cleaned up
    assert key not in plant.historical_tick_requests



async def test_concurrent_different_symbols(history_plant_mock):
    """
    Bug B: Two concurrent requests used to share one event. The first response
    would wake the second caller prematurely. Now each request has its own event.
    """
    plant = history_plant_mock

    async def fire_responses(data_rows):
        await asyncio.sleep(0.01)

        keys = set()
        for symbol, data in data_rows:
            key = f"{symbol}_CME_{int(TimeBarType.MINUTE_BAR)}_1"
            keys.add(key)

            plant._response_to_dict = MagicMock(return_value=data)

            await plant._process_response(
                MagicMock(
                    template_id=203,
                    user_msg=[key]
                )
            )

            await asyncio.sleep(0.01)

        for key in keys:
            plant.historical_time_bar_requests[key].done.set()


    # Fire interleaved responses
    asyncio.create_task(
        fire_responses([
            ["MNQM6", {"x": 1, "marker": 1777300260}],
            ["MESM6", {"y": 1, "marker": 1777300260}],
            ["MNQM6", {"x": 2, "marker": 1777300260}],
        ])
    )

    result_a, result_b = await asyncio.gather(
        plant.get_historical_time_bars(
            symbol="MNQM6", exchange="CME",
            start_time=datetime(2026, 4, 13, 0), end_time=datetime(2026, 4, 13, 0, 1),
            bar_type=TimeBarType.MINUTE_BAR, bar_type_periods=1,
        ),
        plant.get_historical_time_bars(
            symbol="MESM6", exchange="CME",
            start_time=datetime(2026, 4, 13, 0), end_time=datetime(2026, 4, 13, 0, 1),
            bar_type=TimeBarType.MINUTE_BAR, bar_type_periods=1,
        ),
    )

    assert len(result_a) == 2
    assert result_a[0]["x"] == 1
    assert result_a[1]["x"] == 2

    assert len(result_b) == 1
    assert result_b[0]["y"] == 1

async def test_historical_time_bar_pagination(history_plant_mock):
    """
    When Rithmic truncates a historical time bar replay, the client should
    request additional pages until the returned bars cover the requested end_time.

    Rithmic seems to label time bars by end timestamp. So a request covering 10:00 to
    10:04 can return bars labeled 10:01, 10:02, 10:03, 10:04, 10:05.
    """
    plant = history_plant_mock

    symbol = "MNQM6"
    exchange = "CME"
    bar_type = TimeBarType.MINUTE_BAR
    bar_type_periods = 1

    key = f"{symbol}_{exchange}_{bar_type}_{bar_type_periods}"

    # Marker values returned by Rithmic for the request:
    #
    # 1777644060 -> 10:01
    # 1777644120 -> 10:02
    # 1777644180 -> 10:03
    # 1777644240 -> 10:04
    # 1777644300 -> 10:05

    start_dt = datetime(2026, 5, 1, 10, 0)
    end_dt = datetime(2026, 5, 1, 10, 4)

    chunks = [
        # First request response: truncated before covering end_time.
        [
            {"marker": 1777644060, "page": 1},
            {"marker": 1777644120, "page": 1},
            None,  # End msg
        ],

        # Second request response: now covers/passes end_time.
        [
            {"marker": 1777644180, "page": 2},
            {"marker": 1777644240, "page": 2},
            {"marker": 1777644300, "page": 2},
            None,  # End msg
        ],
    ]

    async def emit_chunk(chunk):
        for row in chunk:
            if row is None:
                # Rithmic terminal/completion message for this page.
                await plant._process_response(
                    MagicMock(
                        template_id=203,
                        rp_code=["0"],
                        rq_handler_rp_code=[],
                        user_msg=[key],
                    )
                )
                continue

            plant._response_to_dict = MagicMock(return_value=row)

            await plant._process_response(
                MagicMock(
                    template_id=203,
                    rp_code=[],
                    rq_handler_rp_code=["data"],
                    user_msg=[key],
                )
            )

    send_count = 0

    async def fake_send_request(**kwargs):
        nonlocal send_count

        chunk = chunks[send_count]
        send_count += 1

        # Schedule responses asynchronously so get_historical_time_bars()
        # can enter _wait_for_historical_request_completion().
        asyncio.create_task(emit_chunk(chunk))

    plant._send_request = AsyncMock(side_effect=fake_send_request)

    result = await plant.get_historical_time_bars(
        symbol=symbol,
        exchange=exchange,
        start_time=start_dt,
        end_time=end_dt,
        bar_type=bar_type,
        bar_type_periods=bar_type_periods,
        max_pages=5,
    )

    assert [row["marker"] for row in result] == [
        1777644060,
        1777644120,
        1777644180,
        1777644240,
        1777644300,
    ]

    assert [row["page"] for row in result] == [1, 1, 2, 2, 2]

    # One request for the first page, one request for the second page.
    assert plant._send_request.await_count == 2
    assert send_count == 2

    # Request state should be cleaned up after completion.
    assert key not in plant.historical_time_bar_requests

    first_call = plant._send_request.await_args_list[0].kwargs
    second_call = plant._send_request.await_args_list[1].kwargs

    assert first_call["template_id"] == 202
    assert first_call["user_msg"] == key
    assert first_call["start_index"] == 1777644000
    assert first_call["finish_index"] == 1777644240

    assert second_call["template_id"] == 202
    assert second_call["user_msg"] == key

    # Your production code does:
    # next_start_index = request.last_marker + 1
    assert second_call["start_index"] == 1777644120 + 1
    assert second_call["finish_index"] == 1777644240
