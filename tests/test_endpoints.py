import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import suppress

from async_rithmic.exceptions import RithmicErrorResponse
from conftest import load_response_mock_from_filename

async def test_get_front_month_contract(ticker_plant_mock):
    with patch.object(ticker_plant_mock, "_generate_request_id", MagicMock(return_value="NQ")):
        future = asyncio.create_task(
            ticker_plant_mock.get_front_month_contract("NQ", "CME")
        )
        await asyncio.sleep(0.01)

        recv_queue = asyncio.Queue()
        for r in load_response_mock_from_filename(["front_month_contract_NQ"]):
            await recv_queue.put(r)

        async def mock_recv():
            return await recv_queue.get()

        ticker_plant_mock.ws.recv.side_effect = mock_recv

        recv_task = asyncio.create_task(ticker_plant_mock._recv_loop())
        process_task = asyncio.create_task(ticker_plant_mock._process_loop())
        await asyncio.sleep(0.1)

        result = await future
        assert result == "NQU4"

    recv_task.cancel()
    process_task.cancel()
    for task in [recv_task, process_task]:
        with suppress(asyncio.CancelledError):
            await task

async def test_get_front_month_contract_no_data_raises(ticker_plant_mock):
    """Rithmic returns rp_code='7' (no data) → empty response list from
    _send_and_collect. The caller must raise, not silently return None —
    silent None poisoned downstream protobuf calls during the 2026-04-16
    rollover (TypeError: bad argument type for built-in operation)."""
    ticker_plant_mock._send_and_collect = AsyncMock(return_value=[])

    with pytest.raises(RithmicErrorResponse, match="no front-month"):
        await ticker_plant_mock.get_front_month_contract("NQ", "CME")


async def test_get_front_month_contract_empty_symbol_raises(ticker_plant_mock):
    """A response with an empty trading_symbol is also treated as no-data."""
    empty_response = MagicMock()
    empty_response.trading_symbol = ""
    ticker_plant_mock._send_and_collect = AsyncMock(return_value=[empty_response])

    with pytest.raises(RithmicErrorResponse, match="no front-month"):
        await ticker_plant_mock.get_front_month_contract("NQ", "CME")