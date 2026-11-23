import pytest

from async_rithmic import protocol_buffers as pb
from async_rithmic.exceptions import RithmicNoDataResponse
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
