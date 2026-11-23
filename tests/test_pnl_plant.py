import pytest

from async_rithmic import protocol_buffers as pb
from async_rithmic.exceptions import RithmicNoDataResponse
from conftest import answer_requests, make_client


def answer_snapshots(plant, answers):
    """Answer each PnL snapshot request with the records and response code given for its account."""
    requested_accounts = []

    def respond(request):
        requested_accounts.append(request.account_id)
        records, rp_code = answers[request.account_id]
        terminal = pb.response_pnl_position_snapshot_pb2.ResponsePnLPositionSnapshot(
            template_id=403,
            user_msg=request.user_msg,
            rp_code=[rp_code],
        )
        return [*records, terminal]

    answer_requests(plant, respond)
    return requested_accounts


def position(account_id):
    return pb.instrument_pnl_position_update_pb2.InstrumentPnLPositionUpdate(
        template_id=450, is_snapshot=True, account_id=account_id,
    )


def account_summary(account_id):
    return pb.account_pnl_position_update_pb2.AccountPnLPositionUpdate(
        template_id=451, is_snapshot=True, account_id=account_id,
    )


@pytest.mark.parametrize(
    ("method_name", "snapshot"),
    [
        ("list_positions", position),
        ("list_account_summary", account_summary),
    ],
)
async def test_pnl_snapshots_without_account_id_include_all_accounts(method_name, snapshot):
    plant = make_client().plants["pnl"]
    first_snapshot = snapshot("account-1")
    second_snapshot = snapshot("account-2")
    requested_accounts = answer_snapshots(plant, {
        "account-1": ([first_snapshot], "0"),
        "account-2": ([second_snapshot], "0"),
    })

    result = await getattr(plant, method_name)()

    assert result == [first_snapshot, second_snapshot]
    assert requested_accounts == ["account-1", "account-2"]


async def test_pnl_snapshot_with_account_id_remains_single_account():
    plant = make_client().plants["pnl"]
    snapshot = position("account-2")
    requested_accounts = answer_snapshots(plant, {"account-2": ([snapshot], "0")})

    result = await plant.list_positions(account_id="account-2")

    assert result == [snapshot]
    assert requested_accounts == ["account-2"]


@pytest.mark.parametrize("kwargs", [dict(account_id="account-2"), dict()], ids=["one-account", "all-accounts"])
async def test_pnl_snapshot_no_data_raises_instead_of_partial_records(kwargs):
    plant = make_client().plants["pnl"]
    answer_snapshots(plant, {
        "account-1": ([position("account-1")], "0"),
        "account-2": ([position("account-2")], "7"),
    })

    with pytest.raises(RithmicNoDataResponse):
        await plant.list_positions(**kwargs)
