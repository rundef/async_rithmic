from unittest.mock import MagicMock, AsyncMock
from pattern_kit import Event

from async_rithmic import protocol_buffers as pb

from conftest import load_response_mock_from_filename

async def test_get_front_month_contract(ticker_plant_mock):
    responses = load_response_mock_from_filename([
        "front_month_contract_NQ",
    ])

    ticker_plant_mock.ws.recv.side_effect = responses

    fmc = await ticker_plant_mock.get_front_month_contract("NQ", "CME")
    assert fmc == "NQU4"

async def test_race_condition(ticker_plant_mock):
    """
    When user sends any request and we receive an unrelated ws response (e.g. a fill or mkt data update)
    while waiting for the response to the user's request -> it should be handled correctly
    """

    on_tick = MagicMock()

    ticker_plant_mock.client.on_tick = Event()
    ticker_plant_mock.client.on_tick += on_tick

    ticker_plant_mock.ws.recv = AsyncMock(side_effect=[None] * 3)
    ticker_plant_mock._convert_bytes_to_response = MagicMock(
        side_effect=[
            pb.response_search_symbols_pb2.ResponseSearchSymbols(template_id=110, rp_code=[]),
            pb.best_bid_offer_pb2.BestBidOffer(template_id=151, ssboe=1731092410, usecs=164409),
            pb.response_search_symbols_pb2.ResponseSearchSymbols(template_id=110, rp_code=["0"]),
        ]
    )

    results = await ticker_plant_mock.search_symbols("Test")
    assert len(results) == 1
    assert all(r.template_id == 110 for r in results)

    assert on_tick.call_count == 1
