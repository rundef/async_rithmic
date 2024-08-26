from rithmic import RithmicTickerApi
from tests.unit.fixtures.api_fixtures import set_ws_messages
from tests.unit.fixtures.mocked_messages import BASE_SEND, BASE_RECV


def test_order_api_login(ticker_api_ws_mock):
    ticker_api, ws_mock = ticker_api_ws_mock
    assert isinstance(ticker_api, RithmicTickerApi)
    set_ws_messages(ws_mock, BASE_SEND, BASE_RECV)
    ticker_api.connect_and_login()
    assert ticker_api.streams_consuming_count == 0
    assert ticker_api.consuming_subscription is False
