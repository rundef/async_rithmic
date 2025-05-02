from unittest.mock import MagicMock
from datetime import datetime
import pytz

from async_rithmic.plants import TickerPlant
from async_rithmic import protocol_buffers as pb

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


def test_datetime_to_utc():

    plant = TickerPlant(MagicMock())

    ny_tz = pytz.timezone("America/New_York")
    dt = ny_tz.localize(datetime(2024, 11, 8, 17, 29, 0))

    dt = plant._datetime_to_utc(dt)
    assert dt == datetime(2024, 11, 8, 22, 29, 0, tzinfo=pytz.utc)

def test_ssboe_usecs_conversion():
    plant = TickerPlant(MagicMock())

    inputs = 1731092410, 164409

    dt = plant._ssboe_usecs_to_datetime(*inputs)
    assert dt == datetime(2024, 11, 8, 19, 0, 10, 164409, tzinfo=pytz.utc)

    output = plant._datetime_to_ssboe_usecs(dt)
    assert output == inputs

