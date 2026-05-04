"""
Regression tests for the historical data race conditions fixed via per-request events.

Two scenarios that previously crashed:
  A) Empty response (Rithmic returns only the is_last_bar marker → KeyError on pop).
  B) Concurrent requests for different symbols (shared event got overwritten).
"""
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
