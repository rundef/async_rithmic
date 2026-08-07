import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone
from pattern_kit import Event

import pytest

from async_rithmic.plants import HistoryPlant
from async_rithmic import ReconnectionSettings
from async_rithmic.exceptions import (
    HistoricalDataConnectionError,
    HistoricalDataIncompleteError,
    HistoricalDataPaginationError,
    RithmicErrorResponse,
)
from async_rithmic.enums import TimeBarType


def tick_response(key, ssboes, usecs, payload=None, terminal=False):
    if not terminal:
        # A replay response represents one tick, with duplicated timestamp fields.
        ssboes = [ssboes[0], ssboes[0]]
        usecs = [usecs[0], usecs[0]]

    response = MagicMock(
        template_id=207,
        rp_code=["0"] if terminal else [],
        rq_handler_rp_code=[] if terminal else ["data"],
        user_msg=[key],
        data_bar_ssboe=ssboes,
        data_bar_usecs=usecs,
        data_bar_seq_num=[],
    )
    response.payload = payload or {}
    return response


def configure_tick_responses(plant, pages):
    def response_to_dict(response):
        data = response.payload.copy()
        if response.data_bar_ssboe:
            data.setdefault("data_bar_ssboe", [response.data_bar_ssboe[0]])
        if response.data_bar_usecs:
            data.setdefault("data_bar_usecs", [response.data_bar_usecs[0]])
        return data

    plant._response_to_dict = response_to_dict
    calls = []

    async def emit_page(page, key):
        for ssboes, usecs, payload in page:
            await plant._process_response(
                tick_response(
                    key,
                    ssboes,
                    usecs,
                    payload,
                )
            )
        await plant._process_response(
            tick_response(key, [], [], terminal=True)
        )

    def consume_task_exception(task):
        if not task.cancelled():
            task.exception()

    async def fake_send_request(**kwargs):
        calls.append(kwargs)
        page = pages[len(calls) - 1]
        task = asyncio.create_task(emit_page(page, kwargs["user_msg"]))
        task.add_done_callback(consume_task_exception)

    plant._send_request = AsyncMock(side_effect=fake_send_request)
    return calls


@pytest.fixture
def history_plant_mock():
    client = MagicMock()
    client.retry_settings = MagicMock(max_retries=1, timeout=3, jitter_range=None)
    client.on_disconnected = Event()
    client.on_historical_time_bar = Event()
    client.on_historical_tick = Event()

    plant = HistoryPlant(client)
    plant.ws = AsyncMock()
    # Stub the send to avoid real network
    plant._send_request = AsyncMock(return_value=None)

    return plant


async def test_empty_response_returns_empty_list(history_plant_mock):
    """
    Bug A: When Rithmic returns only the is_last_bar marker (no data bars),
    the code used to raise KeyError on .pop(key). Now it returns [].
    """
    plant = history_plant_mock
    key = f"MNQM6_CME_{int(TimeBarType.MINUTE_BAR)}_1"

    # Simulate the is_last_bar marker arriving right after the request is sent
    async def trigger_empty_response():
        await asyncio.sleep(0.01)
        await plant._process_response(
            MagicMock(
                template_id=203,
                rp_code=['0'],
                user_msg=[key]
            )
        )

    asyncio.create_task(trigger_empty_response())

    result = await plant.get_historical_time_bars(
        symbol="MNQM6",
        exchange="CME",
        start_time=datetime(2026, 4, 13, 0, 0),
        end_time=datetime(2026, 4, 13, 0, 1),
        bar_type=TimeBarType.MINUTE_BAR,
        bar_type_periods=1,
    )
    assert result == []
    # Events dict is cleaned up
    assert key not in plant.historical_time_bar_requests


async def test_empty_tick_response_returns_empty_list(history_plant_mock):
    """Same as Bug A but for tick data."""
    plant = history_plant_mock
    key = f"MNQM6_CME"

    # Simulate the is_last_bar marker arriving right after the request is sent
    async def trigger_empty_response():
        await asyncio.sleep(0.01)
        await plant._process_response(
            MagicMock(
                template_id=207,
                rp_code=[],
                rq_handler_rp_code=[],
                user_msg=[key]
            )
        )

    asyncio.create_task(trigger_empty_response())

    result = await plant.get_historical_tick_data(
        symbol="MNQM6", exchange="CME",
        start_time=datetime(2026, 4, 13, 0), end_time=datetime(2026, 4, 13, 0, 1),
    )
    assert result == []
    # Events dict is cleaned up
    assert key not in plant.historical_tick_requests



async def test_partial_tick_page_completes_without_continuation(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 4)
    plant = history_plant_mock
    key = "MNQM6_CME"
    calls = configure_tick_responses(
        plant,
        [[
            ([100], [900_000], {"id": "only"}),
            ([100], [950_000], {"id": "last"}),
        ]],
    )

    result = await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime.fromtimestamp(100, tz=timezone.utc),
        datetime.fromtimestamp(200, tz=timezone.utc),
    )

    assert [row["id"] for row in result] == ["only", "last"]
    assert len(calls) == 1
    assert key not in plant.historical_tick_requests


async def test_full_tick_page_replays_and_crops_final_second(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 4)
    plant = history_plant_mock
    callback_ids = []

    async def on_tick(data):
        callback_ids.append(data["id"])

    plant.client.on_historical_tick += on_tick
    calls = configure_tick_responses(
        plant,
        [
            [
                ([100], [900_000], {"id": "safe"}),
                ([101], [0], {"id": "boundary-zero"}),
                ([101], [100_000], {"id": "boundary-a"}),
                ([101], [200_000], {"id": "boundary-b"}),
            ],
            [
                ([101], [0], {"id": "boundary-zero"}),
                ([101], [100_000], {"id": "boundary-a"}),
                ([101], [200_000], {"id": "boundary-b"}),
            ],
        ],
    )

    result = await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime.fromtimestamp(100, tz=timezone.utc),
        datetime.fromtimestamp(200, tz=timezone.utc),
    )

    assert [row["id"] for row in result] == [
        "safe", "boundary-zero", "boundary-a", "boundary-b"
    ]
    assert calls[1]["start_index"] == 101
    assert sum(row["id"] == "boundary-zero" for row in result) == 1
    assert sum(row["id"] == "boundary-a" for row in result) == 1
    assert sum(row["id"] == "boundary-b" for row in result) == 1
    assert callback_ids == [row["id"] for row in result]


async def test_duplicate_timestamps_in_one_response_produce_one_tick(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 4)
    plant = history_plant_mock
    callback_records = []

    async def on_tick(data):
        callback_records.append(data)

    plant.client.on_historical_tick += on_tick
    configure_tick_responses(
        plant,
        [[
            ([101, 101], [200_000, 200_000], {
                "data_bar_seq_num": ["tick-sequence"],
                "price": 101.5,
                "quantity": 2,
            }),
        ]],
    )

    result = await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime.fromtimestamp(100, tz=timezone.utc),
        datetime.fromtimestamp(200, tz=timezone.utc),
    )

    assert len(result) == 1
    assert result[0]["data_bar_seq_num"] == ["tick-sequence"]
    assert result[0]["price"] == 101.5
    assert result[0]["quantity"] == 2
    assert result[0]["data_bar_ssboe"] == [101]
    assert result[0]["data_bar_usecs"] == [200_000]
    assert callback_records == result


async def test_identical_ticks_from_separate_responses_are_not_deduplicated(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 4)
    plant = history_plant_mock
    calls = configure_tick_responses(
        plant,
        [[
            ([100], [500_000], {
                "price": 100.25,
                "quantity": 2,
                "side": "B",
            }),
            ([100], [500_000], {
                "price": 100.25,
                "quantity": 2,
                "side": "B",
            }),
        ]],
    )

    result = await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime.fromtimestamp(100, tz=timezone.utc),
        datetime.fromtimestamp(200, tz=timezone.utc),
    )

    assert len(result) == 2
    assert result[0] == result[1]
    assert len(calls) == 1


async def test_tick_page_is_stably_sorted_before_pagination(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 4)
    plant = history_plant_mock
    calls = configure_tick_responses(
        plant,
        [
            [
                ([101], [200_000], {"id": "latest"}),
                ([100], [500_000], {"id": "first"}),
                ([100], [500_000], {"id": "second"}),
                ([100], [900_000], {"id": "middle"}),
            ],
            [([101], [200_000], {"id": "latest"})],
        ],
    )

    result = await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime.fromtimestamp(100, tz=timezone.utc),
        datetime.fromtimestamp(200, tz=timezone.utc),
    )

    assert [row["id"] for row in result] == [
        "first", "second", "middle", "latest"
    ]
    assert calls[1]["start_index"] == 101


async def test_single_second_overflow_raises_to_public_caller(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 4)
    plant = history_plant_mock
    calls = configure_tick_responses(
        plant,
        [[
            ([100], [100_000], {"id": "a"}),
            ([100], [200_000], {"id": "b"}),
            ([100], [300_000], {"id": "c"}),
            ([100], [400_000], {"id": "d"}),
        ]],
    )

    with pytest.raises(HistoricalDataPaginationError, match="more than one page"):
        await plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
        )

    assert len(calls) == 1
    assert not plant.historical_tick_requests


async def test_max_pages_in_strict_mode_fails_without_partial_success(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 4)
    plant = history_plant_mock
    calls = configure_tick_responses(
        plant,
        [[
            ([100], [900_000], {"id": "safe"}),
            ([101], [0], {"id": "boundary-zero"}),
            ([101], [100_000], {"id": "boundary-a"}),
            ([101], [200_000], {"id": "boundary-b"}),
        ]],
    )

    with pytest.raises(HistoricalDataIncompleteError):
        await plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
            max_pages=1,
        )

    assert len(calls) == 1
    assert not plant.historical_tick_requests


async def test_max_pages_can_explicitly_allow_a_partial_result(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 4)
    plant = history_plant_mock
    configure_tick_responses(
        plant,
        [[
            ([100], [900_000], {"id": "safe"}),
            ([101], [0], {"id": "boundary-zero"}),
            ([101], [100_000], {"id": "boundary-a"}),
            ([101], [200_000], {"id": "boundary-b"}),
        ]],
    )

    result = await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime.fromtimestamp(100, tz=timezone.utc),
        datetime.fromtimestamp(200, tz=timezone.utc),
        max_pages=1,
        strict=False,
    )

    assert [row["id"] for row in result] == ["safe"]


@pytest.mark.parametrize("max_pages", [0, -1])
async def test_invalid_max_pages_fails_before_provider_io(
    history_plant_mock, max_pages
):
    plant = history_plant_mock

    with pytest.raises(ValueError, match="max_pages"):
        await plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
            max_pages=max_pages,
        )

    plant._send_request.assert_not_awaited()
    assert not plant.historical_tick_requests


async def test_historical_callback_failure_completes_request_with_original_error(
    history_plant_mock
):
    plant = history_plant_mock
    callback_error = RuntimeError("historical callback failed")

    async def failing_callback(data):
        raise callback_error

    plant.client.on_historical_tick += failing_callback
    configure_tick_responses(
        plant,
        [[([100], [900_000], {"id": "delivered-before-failure"})]],
    )

    with pytest.raises(RuntimeError, match="historical callback failed") as exc_info:
        await plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
        )

    assert exc_info.value is callback_error
    assert not plant.historical_tick_requests


async def test_history_disconnect_fails_active_request_without_waiting_for_timeout(
    history_plant_mock
):
    plant = history_plant_mock
    plant._send_request = AsyncMock(return_value=None)

    request_task = asyncio.create_task(
        plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
            idle_timeout=30,
        )
    )
    await asyncio.sleep(0)
    assert plant.historical_tick_requests

    await plant.client.on_disconnected.call_async(plant.plant_type)

    with pytest.raises(HistoricalDataConnectionError):
        await request_task

    assert not plant.historical_tick_requests


async def test_new_historical_request_can_start_after_disconnect(
    history_plant_mock
):
    plant = history_plant_mock
    plant._send_request = AsyncMock(return_value=None)

    request_task = asyncio.create_task(
        plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
            idle_timeout=30,
        )
    )
    await asyncio.sleep(0)
    await plant.client.on_disconnected.call_async(plant.plant_type)

    with pytest.raises(HistoricalDataConnectionError):
        await request_task

    configure_tick_responses(
        plant,
        [[([100], [900_000], {"id": "after-reconnect"})]],
    )
    result = await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime.fromtimestamp(100, tz=timezone.utc),
        datetime.fromtimestamp(200, tz=timezone.utc),
    )

    assert [row["id"] for row in result] == ["after-reconnect"]
    assert not plant.historical_tick_requests


async def test_reconnect_does_not_resume_failed_historical_request(
    history_plant_mock
):
    plant = history_plant_mock
    plant._send_request = AsyncMock(return_value=None)
    plant.client.reconnection_settings = ReconnectionSettings(
        max_retries=1,
        backoff_type="constant",
        interval=0,
    )
    plant._connect = AsyncMock()
    plant._start_io_tasks = AsyncMock()
    plant._stop_io_tasks = AsyncMock()
    plant._login = AsyncMock()

    request_task = asyncio.create_task(
        plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
            idle_timeout=30,
        )
    )
    await asyncio.sleep(0)
    await plant.client.on_disconnected.call_async(plant.plant_type)

    with pytest.raises(HistoricalDataConnectionError):
        await request_task

    reconnect_task = asyncio.create_task(plant._reconnect_loop())
    plant._disconnect_event.set()
    await asyncio.sleep(0.01)
    reconnect_task.cancel()
    await reconnect_task

    assert plant._send_request.await_count == 1
    assert not plant.historical_tick_requests

    configure_tick_responses(
        plant,
        [[([100], [900_000], {"id": "after-reconnect"})]],
    )
    result = await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime.fromtimestamp(100, tz=timezone.utc),
        datetime.fromtimestamp(200, tz=timezone.utc),
    )

    assert [row["id"] for row in result] == ["after-reconnect"]
    assert not plant.historical_tick_requests


async def test_cancelled_historical_request_remains_cancelled(history_plant_mock):
    plant = history_plant_mock
    plant._send_request = AsyncMock(return_value=None)

    request_task = asyncio.create_task(
        plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
            idle_timeout=30,
        )
    )
    await asyncio.sleep(0)
    request_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await request_task

    assert not plant.historical_tick_requests


async def test_continuation_timestamp_before_boundary_fails_closed(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 2)
    plant = history_plant_mock
    configure_tick_responses(
        plant,
        [
            [
                ([100], [900_000], {"id": "safe"}),
                ([101], [0], {"id": "boundary"}),
            ],
            [([100], [950_000], {"id": "stale"})],
        ],
    )

    with pytest.raises(HistoricalDataPaginationError, match="before"):
        await plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
        )

    assert not plant.historical_tick_requests


async def test_malformed_tick_timestamp_arrays_fail_closed(history_plant_mock):
    plant = history_plant_mock
    key = "MNQM6_CME"
    plant._response_to_dict = lambda response: {}

    async def fake_send_request(**kwargs):
        await plant._process_response(
            MagicMock(
                template_id=207,
                rp_code=[],
                rq_handler_rp_code=["data"],
                user_msg=[key],
                data_bar_ssboe=[100, 101],
                data_bar_usecs=[900_000, 900_000],
            )
        )

    plant._send_request = AsyncMock(side_effect=fake_send_request)

    with pytest.raises(HistoricalDataPaginationError, match="non-repeated"):
        await plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
        )

    assert not plant.historical_tick_requests


async def test_empty_tick_continuation_completes_without_duplicate_callbacks(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 2)
    plant = history_plant_mock
    callback_ids = []

    async def on_tick(data):
        callback_ids.append(data["id"])

    plant.client.on_historical_tick += on_tick
    calls = configure_tick_responses(
        plant,
        [[([100], [900_000], {"id": "safe"}), ([101], [0], {"id": "boundary"})], []],
    )

    result = await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime.fromtimestamp(100, tz=timezone.utc),
        datetime.fromtimestamp(200, tz=timezone.utc),
    )

    assert [row["id"] for row in result] == ["safe"]
    assert callback_ids == ["safe"]
    assert len(calls) == 2
    assert calls[1]["start_index"] == 101


async def test_tick_provider_error_does_not_emit_buffered_partial_page(
    history_plant_mock
):
    plant = history_plant_mock
    key = "MNQM6_CME"
    callback_ids = []
    calls = []

    async def on_tick(data):
        callback_ids.append(data["id"])

    plant.client.on_historical_tick += on_tick
    plant._response_to_dict = lambda response: response.payload.copy()

    async def fake_send_request(**kwargs):
        calls.append(kwargs)
        await plant._process_response(
            tick_response(key, [100], [900_000], {"id": "discard-me"})
        )
        await plant._process_response(
            MagicMock(
                template_id=207,
                rp_code=["8"],
                rq_handler_rp_code=[],
                user_msg=[key],
            )
        )

    plant._send_request = AsyncMock(side_effect=fake_send_request)

    with pytest.raises(RithmicErrorResponse):
        await plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
        )

    assert callback_ids == []
    assert len(calls) == 1
    assert key not in plant.historical_tick_requests


async def test_tick_continuation_send_error_completes_and_cleans_up(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 2)
    plant = history_plant_mock
    key = "MNQM6_CME"
    calls = []

    async def fake_send_request(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            await plant._process_response(
                tick_response(key, [100], [900_000], {"id": "safe"})
            )
            await plant._process_response(
                tick_response(key, [101], [0], {"id": "boundary"})
            )
            await plant._process_response(
                tick_response(key, [], [], terminal=True)
            )
        else:
            raise RuntimeError("continuation send failed")

    plant._send_request = AsyncMock(side_effect=fake_send_request)

    with pytest.raises(RuntimeError, match="continuation send failed"):
        await plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
        )

    assert len(calls) == 2
    assert calls[1]["start_index"] == 101
    assert key not in plant.historical_tick_requests


async def test_subsecond_tick_bounds_are_floored(history_plant_mock):
    plant = history_plant_mock
    await plant.get_historical_tick_data(
        "MNQM6", "CME",
        datetime(2026, 4, 13, 0, 0, 0, 900_000, tzinfo=timezone.utc),
        datetime(2026, 4, 13, 0, 1, 0, 100_000, tzinfo=timezone.utc),
        wait=False,
    )

    request = plant._send_request.await_args.kwargs
    assert request["start_index"] == int(datetime(
        2026, 4, 13, 0, tzinfo=timezone.utc
    ).timestamp())
    assert request["finish_index"] == int(datetime(
        2026, 4, 13, 0, 1, tzinfo=timezone.utc
    ).timestamp())


async def test_repeated_full_page_fails_instead_of_looping(
    history_plant_mock, monkeypatch
):
    import importlib

    history_module = importlib.import_module("async_rithmic.plants.history")
    monkeypatch.setattr(history_module, "HISTORICAL_TICK_PAGE_SIZE", 4)
    plant = history_plant_mock
    callback_ids = []

    async def on_tick(data):
        callback_ids.append(data["id"])

    plant.client.on_historical_tick += on_tick
    page = [
        ([100], [900_000], {"id": "safe"}),
        ([101], [0], {"id": "boundary-zero"}),
        ([101], [100_000], {"id": "boundary-a"}),
        ([101], [200_000], {"id": "boundary-b"}),
    ]
    calls = configure_tick_responses(plant, [page, page])

    with pytest.raises(HistoricalDataPaginationError):
        await plant.get_historical_tick_data(
            "MNQM6", "CME",
            datetime.fromtimestamp(100, tz=timezone.utc),
            datetime.fromtimestamp(200, tz=timezone.utc),
        )

    assert len(calls) == 2
    assert callback_ids == ["safe"]
    assert not plant.historical_tick_requests


async def test_concurrent_different_symbols(history_plant_mock):
    """
    Bug B: Two concurrent requests used to share one event. The first response
    would wake the second caller prematurely. Now each request has its own event.
    """
    plant = history_plant_mock

    async def fire_responses(data_rows):
        await asyncio.sleep(0.01)

        keys = set()
        for symbol, data in data_rows:
            key = f"{symbol}_CME_{int(TimeBarType.MINUTE_BAR)}_1"
            keys.add(key)

            plant._response_to_dict = MagicMock(return_value=data)

            await plant._process_response(
                MagicMock(
                    template_id=203,
                    user_msg=[key]
                )
            )

            await asyncio.sleep(0.01)

        for key in keys:
            plant.historical_time_bar_requests[key].done.set()


    # Fire interleaved responses
    asyncio.create_task(
        fire_responses([
            ["MNQM6", {"x": 1, "marker": 1777300260}],
            ["MESM6", {"y": 1, "marker": 1777300260}],
            ["MNQM6", {"x": 2, "marker": 1777300260}],
        ])
    )

    result_a, result_b = await asyncio.gather(
        plant.get_historical_time_bars(
            symbol="MNQM6", exchange="CME",
            start_time=datetime(2026, 4, 13, 0), end_time=datetime(2026, 4, 13, 0, 1),
            bar_type=TimeBarType.MINUTE_BAR, bar_type_periods=1,
        ),
        plant.get_historical_time_bars(
            symbol="MESM6", exchange="CME",
            start_time=datetime(2026, 4, 13, 0), end_time=datetime(2026, 4, 13, 0, 1),
            bar_type=TimeBarType.MINUTE_BAR, bar_type_periods=1,
        ),
    )

    assert len(result_a) == 2
    assert result_a[0]["x"] == 1
    assert result_a[1]["x"] == 2

    assert len(result_b) == 1
    assert result_b[0]["y"] == 1

async def test_historical_time_bar_pagination(history_plant_mock):
    """
    When Rithmic truncates a historical time bar replay, the client should
    request additional pages until the returned bars cover the requested end_time.

    Rithmic seems to label time bars by end timestamp. So a request covering 10:00 to
    10:04 can return bars labeled 10:01, 10:02, 10:03, 10:04, 10:05.
    """
    plant = history_plant_mock

    symbol = "MNQM6"
    exchange = "CME"
    bar_type = TimeBarType.MINUTE_BAR
    bar_type_periods = 1

    key = f"{symbol}_{exchange}_{bar_type}_{bar_type_periods}"

    # Marker values returned by Rithmic for the request:
    #
    # 1777644060 -> 10:01
    # 1777644120 -> 10:02
    # 1777644180 -> 10:03
    # 1777644240 -> 10:04
    # 1777644300 -> 10:05

    start_dt = datetime(2026, 5, 1, 14, 0, tzinfo=timezone.utc)
    end_dt = datetime(2026, 5, 1, 14, 4, tzinfo=timezone.utc)

    chunks = [
        # First request response: truncated before covering end_time.
        [
            {"marker": 1777644060, "page": 1},
            {"marker": 1777644120, "page": 1},
            None,  # End msg
        ],

        # Second request response: now covers/passes end_time.
        [
            {"marker": 1777644180, "page": 2},
            {"marker": 1777644240, "page": 2},
            {"marker": 1777644300, "page": 2},
            None,  # End msg
        ],
    ]

    async def emit_chunk(chunk):
        for row in chunk:
            if row is None:
                # Rithmic terminal/completion message for this page.
                await plant._process_response(
                    MagicMock(
                        template_id=203,
                        rp_code=["0"],
                        rq_handler_rp_code=[],
                        user_msg=[key],
                    )
                )
                continue

            plant._response_to_dict = MagicMock(return_value=row)

            await plant._process_response(
                MagicMock(
                    template_id=203,
                    rp_code=[],
                    rq_handler_rp_code=["data"],
                    user_msg=[key],
                )
            )

    send_count = 0

    async def fake_send_request(**kwargs):
        nonlocal send_count

        chunk = chunks[send_count]
        send_count += 1

        # Schedule responses asynchronously so get_historical_time_bars()
        # can enter _wait_for_historical_request_completion().
        asyncio.create_task(emit_chunk(chunk))

    plant._send_request = AsyncMock(side_effect=fake_send_request)

    result = await plant.get_historical_time_bars(
        symbol=symbol,
        exchange=exchange,
        start_time=start_dt,
        end_time=end_dt,
        bar_type=bar_type,
        bar_type_periods=bar_type_periods,
        max_pages=5,
    )

    assert [row["marker"] for row in result] == [
        1777644060,
        1777644120,
        1777644180,
        1777644240,
        1777644300,
    ]

    assert [row["page"] for row in result] == [1, 1, 2, 2, 2]

    # One request for the first page, one request for the second page.
    assert plant._send_request.await_count == 2
    assert send_count == 2

    # Request state should be cleaned up after completion.
    assert key not in plant.historical_time_bar_requests

    first_call = plant._send_request.await_args_list[0].kwargs
    second_call = plant._send_request.await_args_list[1].kwargs

    assert first_call["template_id"] == 202
    assert first_call["user_msg"] == key
    assert first_call["start_index"] == 1777644000
    assert first_call["finish_index"] == 1777644240

    assert second_call["template_id"] == 202
    assert second_call["user_msg"] == key

    # next_start_index = request.last_marker + 1
    assert second_call["start_index"] == 1777644120 + 1
    assert second_call["finish_index"] == 1777644240
