import asyncio
from unittest.mock import patch, MagicMock
from contextlib import suppress

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

