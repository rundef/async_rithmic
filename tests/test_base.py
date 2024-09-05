from unittest.mock import MagicMock, AsyncMock, patch
from websockets import ConnectionClosedError, ConnectionClosedOK

from rithmic.plants import TickerPlant
from rithmic.event import Event

import rithmic.protocol_buffers as pb
from conftest import load_response_mock_from_filename

def test_convert_request_to_bytes():
    rq = pb.request_login_pb2.RequestLogin()
    rq.template_id = 10
    rq.template_version = "3.9"
    rq.user = 'my_username'
    rq.password = 'my_password'
    rq.app_name = 'my_app'
    rq.app_version = 'my_version'
    rq.system_name = 'RITHMIC TEST'
    rq.infra_type = 2

    api = TickerPlant(None)
    result = api._convert_request_to_bytes(rq)
    expected = b'\x00\x00\x00U\x92\xbd?\x06my_app\xa2\xbd?\x0bmy_password\xda\xfb?\x0bmy_username\xda\xad@\nmy_version\xa8\x81K\x02\xe2\x81K\x0cRITHMIC TEST\x92\x82K\x033.9\x98\xb6K\n'
    assert result == expected
    assert isinstance(result, bytes)


def test_convert_bytes_to_response():
    api = TickerPlant(None)
    msg_buf = b'\x00\x00\x00\x17\x98\xb6K\x13\xa0\xa5I\xa5\xa0\xeb\xa8\x06\xa8\xa5I\x8c\xd9.\xf2\xe9@\x010'
    response = api._convert_bytes_to_response(msg_buf)
    assert response.template_id == 19
    assert isinstance(response, pb.response_heartbeat_pb2.ResponseHeartbeat)


async def test_event_callback():
    my_callback1 = AsyncMock()
    my_callback2 = AsyncMock()

    e = Event()
    e += my_callback1
    e += my_callback2

    await e.notify()
    assert my_callback1.call_count == 1
    assert my_callback2.call_count == 1

    e -= my_callback1
    await e.notify()
    assert my_callback1.call_count == 1
    assert my_callback2.call_count == 2


async def test_get_reference_data(ticker_plant_mock):
    responses = load_response_mock_from_filename([
        "reference_data_ES",
    ])

    ticker_plant_mock.ws.recv.side_effect = responses

    response = await ticker_plant_mock.get_reference_data("ES", "CME")

    assert response.product_code == response.symbol == "ES"
    assert response.exchange_symbol == "ESU4"
    assert response.symbol_name == "Front Month for ES - ESU4.CME"
    assert response.exchange == "CME"
    assert response.currency == "USD"
    assert response.expiration_date == "20240920"
    assert response.min_qprice_change == 0.25


async def test_handle_reconnection():
    plant = TickerPlant(MagicMock())
    plant.lock = AsyncMock()
    plant._recv = AsyncMock()
    plant._process_message = AsyncMock()
    plant._send_heartbeat = AsyncMock()
    plant._connect = AsyncMock()
    plant._login = AsyncMock()

    responses = load_response_mock_from_filename([
        "reference_data_ES",
    ])

    plant._recv.side_effect = [
        ConnectionClosedError(rcvd=100, sent=200),
        responses[0],
    ]

    # Patch sleep to avoid actual delay
    with patch('asyncio.sleep', return_value=None) as mock_sleep:
        result = await plant._listen(max_iterations=2)

        # Check that the reconnection logic was triggered
        plant._connect.assert_called()
        plant._login.assert_called()
        mock_sleep.assert_called()  # Reconnection delay

        # Verify that reconnection attempts were made
        assert plant._connect.call_count == 1
        assert plant._login.call_count == 1

        # Ensure that the listener kept running after the first reconnection
        assert result is None
