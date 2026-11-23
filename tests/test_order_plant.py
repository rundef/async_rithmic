import asyncio
from unittest.mock import AsyncMock

import pytest
from websockets.exceptions import ConnectionClosedError

from async_rithmic import OrderType, RetrySettings, TransactionType
from async_rithmic import protocol_buffers as pb
from async_rithmic.exceptions import RithmicConnectionLostError, RithmicNoDataResponse
from conftest import answer_requests, make_client


def answer_order_snapshots(plant, answers):
    """Answer each ShowOrders request with the orders and response code given for its account."""
    def respond(request):
        orders, rp_code = answers[request.account_id]
        terminal = pb.response_show_orders_pb2.ResponseShowOrders(
            template_id=321,
            user_msg=request.user_msg,
            rp_code=[rp_code],
        )
        return [*orders, terminal]

    answer_requests(plant, respond)


def order(account_id, order_id):
    return pb.exchange_order_notification_pb2.ExchangeOrderNotification(
        template_id=352, is_snapshot=True, account_id=account_id, user_tag=order_id,
    )


def sent_template_ids(plant):
    return [
        plant._convert_bytes_to_response(call.args[0]).template_id
        for call in plant.ws.send.await_args_list
    ]


async def test_list_orders_no_data_raises_instead_of_partial_records():
    plant = make_client().plants["order"]
    answer_order_snapshots(plant, {"account-1": ([order("account-1", "order-1")], "7")})

    with pytest.raises(RithmicNoDataResponse):
        await plant.list_orders(account_id="account-1")


async def test_get_order_looks_past_an_account_without_data():
    plant = make_client().plants["order"]
    wanted = order("account-2", "order-2")
    answer_order_snapshots(plant, {
        "account-1": ([], "7"),
        "account-2": ([order("account-2", "other-order"), wanted], "0"),
    })

    assert await plant.get_order(order_id="order-2") == wanted


async def test_timeouts_retry_reads_but_never_order_operations():
    plant = make_client(retry_settings=RetrySettings(max_retries=3, timeout=0.05)).plants["order"]
    plant.ws = AsyncMock()

    with pytest.raises(asyncio.TimeoutError):
        await plant.cancel_order(basket_id="basket-1", account_id="account-1")
    assert sent_template_ids(plant) == [316]

    plant.ws.send.reset_mock()
    with pytest.raises(asyncio.TimeoutError):
        await plant.list_orders(account_id="account-1")
    assert sent_template_ids(plant) == [320, 320, 320]


async def test_connection_loss_while_sending_an_order_is_not_resent():
    plant = make_client().plants["order"]
    plant.ws = AsyncMock()
    plant.ws.send.side_effect = ConnectionClosedError(rcvd=None, sent=None)

    # Raised without waiting for a reconnection
    with pytest.raises(RithmicConnectionLostError):
        await asyncio.wait_for(plant.submit_order(
            order_id="order-1",
            symbol="ESZ6",
            exchange="CME",
            qty=1,
            transaction_type=TransactionType.BUY,
            order_type=OrderType.MARKET,
            account_id="account-1",
        ), timeout=1)
    assert plant.ws.send.await_count == 1
