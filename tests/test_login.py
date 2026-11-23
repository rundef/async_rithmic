import asyncio
import logging
import traceback

import pytest

from async_rithmic import RithmicClient
from async_rithmic import protocol_buffers as pb
from async_rithmic.enums import SysInfraType
from async_rithmic.exceptions import RithmicErrorResponse
from conftest import _convert_proto_message_to_bytes, use_local_gateway

USER = "login-user-7f3a"
PASSWORD = "login-password-91c2"


async def test_rejected_login_keeps_credentials_out_of_errors_and_logs(rithmic_server, caplog):
    caplog.set_level(logging.DEBUG, logger="rithmic")
    client = RithmicClient(
        user=USER,
        password=PASSWORD,
        system_name="Rithmic Test",
        app_name="tests",
        app_version="1.0",
        url=rithmic_server.url,
    )
    use_local_gateway(client.plants["order"], rithmic_server)

    async def reject_login():
        gateway = await rithmic_server.connections.get()
        login = pb.request_login_pb2.RequestLogin.FromString((await gateway.recv())[4:])
        await gateway.send(_convert_proto_message_to_bytes(pb.response_login_pb2.ResponseLogin(
            template_id=11,
            user_msg=login.user_msg,
            rp_code=["13", "permission denied"],
        )))
        return login

    gateway = asyncio.create_task(reject_login())
    with pytest.raises(RithmicErrorResponse) as caught:
        await client.connect(plants=[SysInfraType.ORDER_PLANT], plant_connect_delay=0)
    login = await gateway

    assert (login.user, login.password) == (USER, PASSWORD)

    error = caught.value
    error_texts = [str(error), repr(error), "".join(traceback.format_exception(error))]
    library_logs = [record for record in caplog.records if record.name.startswith("rithmic")]
    error_logs = [caplog.handler.format(record) for record in library_logs if record.levelno >= logging.ERROR]
    assert error_logs, "the rejected login should be logged"
    for text in error_texts + error_logs:
        assert USER not in text
        assert PASSWORD not in text
    for record in library_logs:
        assert PASSWORD not in caplog.handler.format(record)
