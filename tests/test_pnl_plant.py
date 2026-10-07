from types import SimpleNamespace
from unittest.mock import AsyncMock, call

import pytest

from async_rithmic.plants import PnlPlant


@pytest.mark.parametrize(
    ("method_name", "expected_template_id"),
    [
        ("list_positions", 450),
        ("list_account_summary", 451),
    ],
)
async def test_pnl_snapshots_without_account_id_include_all_accounts(
    method_name, expected_template_id
):
    plant = PnlPlant(SimpleNamespace(accounts=[
        SimpleNamespace(account_id="account-1"),
        SimpleNamespace(account_id="account-2"),
    ]))
    first_snapshot = SimpleNamespace(account_id="account-1")
    second_snapshot = SimpleNamespace(account_id="account-2")
    plant._send_and_collect = AsyncMock(
        side_effect=[[first_snapshot], [second_snapshot]]
    )

    result = await getattr(plant, method_name)()

    assert result == [first_snapshot, second_snapshot]
    assert plant._send_and_collect.await_args_list == [
        call(
            template_id=402,
            expected_response=dict(template_id=expected_template_id, is_snapshot=True),
            account_id="account-1",
        ),
        call(
            template_id=402,
            expected_response=dict(template_id=expected_template_id, is_snapshot=True),
            account_id="account-2",
        ),
    ]


async def test_pnl_snapshot_with_account_id_remains_single_account():
    plant = PnlPlant(SimpleNamespace(accounts=[
        SimpleNamespace(account_id="account-1"),
        SimpleNamespace(account_id="account-2"),
    ]))
    snapshot = SimpleNamespace(account_id="account-2")
    plant._send_and_collect = AsyncMock(return_value=[snapshot])

    result = await plant.list_positions(account_id="account-2")

    assert result == [snapshot]
    plant._send_and_collect.assert_awaited_once_with(
        template_id=402,
        expected_response=dict(template_id=450, is_snapshot=True),
        account_id="account-2",
    )
