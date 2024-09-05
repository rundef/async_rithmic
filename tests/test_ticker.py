from conftest import load_response_mock_from_filename


async def test_get_front_month_contract(ticker_plant_mock):
    responses = load_response_mock_from_filename([
        "front_month_contract_NQ",
    ])

    ticker_plant_mock.ws.recv.side_effect = responses

    fmc = await ticker_plant_mock.get_front_month_contract("NQ", "CME")
    assert fmc == "NQU4"
