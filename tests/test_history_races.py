"""
Regression tests for the historical data race conditions fixed via per-request events.

Two scenarios that previously crashed:
  A) Empty response (Rithmic returns only the is_last_bar marker → KeyError on pop).
  B) Concurrent requests for different symbols (shared event got overwritten).
"""
import asyncio
from unittest.mock import MagicMock, AsyncMock

import pytest

from async_rithmic.plants import HistoryPlant
from async_rithmic.enums import TimeBarType


@pytest.fixture
def history_plant_mock():
    plant = HistoryPlant(MagicMock())
    plant.ws = AsyncMock()
    plant.client = MagicMock()
    plant.client.retry_settings = MagicMock(max_retries=1, timeout=3, jitter_range=None)
    # Stub the send to avoid real network
    plant._send_and_recv_immediate = AsyncMock(return_value=None)
    return plant


async def test_empty_response_returns_empty_list(history_plant_mock):
    """
    Bug A: When Rithmic returns only the is_last_bar marker (no data bars),
    the code used to raise KeyError on .pop(key). Now it returns [].
    """
    plant = history_plant_mock
    key = f"MNQM6_{int(TimeBarType.MINUTE_BAR)}"

    # Simulate the is_last_bar marker arriving right after the request is sent
    async def trigger_empty_response():
        await asyncio.sleep(0.01)
        event = plant.historical_time_bar_events.get(key)
        if event:
            event.set()

    asyncio.create_task(trigger_empty_response())

    result = await plant.get_historical_time_bars(
        symbol="MNQM6",
        exchange="CME",
        start_time=__import__("datetime").datetime(2026, 4, 13, 0, 0),
        end_time=__import__("datetime").datetime(2026, 4, 13, 0, 1),
        bar_type=TimeBarType.MINUTE_BAR,
        bar_type_periods=1,
    )
    assert result == []
    # Events dict is cleaned up
    assert key not in plant.historical_time_bar_events


async def test_concurrent_different_symbols(history_plant_mock):
    """
    Bug B: Two concurrent requests used to share one event. The first response
    would wake the second caller prematurely. Now each request has its own event.
    """
    plant = history_plant_mock
    import datetime as dt

    async def fire_response_for(symbol, bar_type, delay, data_rows):
        await asyncio.sleep(delay)
        key = f"{symbol}_{int(bar_type)}"
        for row in data_rows:
            plant.historical_time_bar_data[key].append(row)
        event = plant.historical_time_bar_events.get(key)
        if event:
            event.set()

    # Caller A requests MNQM6, caller B requests MESM6 a moment later
    # A's response arrives first with 2 bars; B's response arrives after with 1 bar
    asyncio.create_task(fire_response_for("MNQM6", TimeBarType.MINUTE_BAR, 0.01, [{"x": 1}, {"x": 2}]))
    asyncio.create_task(fire_response_for("MESM6", TimeBarType.MINUTE_BAR, 0.02, [{"y": 1}]))

    result_a, result_b = await asyncio.gather(
        plant.get_historical_time_bars(
            symbol="MNQM6", exchange="CME",
            start_time=dt.datetime(2026, 4, 13, 0), end_time=dt.datetime(2026, 4, 13, 0, 1),
            bar_type=TimeBarType.MINUTE_BAR, bar_type_periods=1,
        ),
        plant.get_historical_time_bars(
            symbol="MESM6", exchange="CME",
            start_time=dt.datetime(2026, 4, 13, 0), end_time=dt.datetime(2026, 4, 13, 0, 1),
            bar_type=TimeBarType.MINUTE_BAR, bar_type_periods=1,
        ),
    )

    assert result_a == [{"x": 1}, {"x": 2}]
    assert result_b == [{"y": 1}]


async def test_empty_tick_response_returns_empty_list(history_plant_mock):
    """Same as Bug A but for tick data."""
    plant = history_plant_mock
    import datetime as dt
    key = "MNQM6"

    async def trigger_empty():
        await asyncio.sleep(0.01)
        event = plant.historical_tick_events.get(key)
        if event:
            event.set()

    asyncio.create_task(trigger_empty())

    result = await plant.get_historical_tick_data(
        symbol="MNQM6", exchange="CME",
        start_time=dt.datetime(2026, 4, 13, 0), end_time=dt.datetime(2026, 4, 13, 0, 1),
    )
    assert result == []
    assert key not in plant.historical_tick_events
