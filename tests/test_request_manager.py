import pytest
import asyncio
import uuid
import random
from collections import namedtuple
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from async_rithmic.helpers.request_manager import RequestManager
from async_rithmic.plants.order import OrderPlant
from async_rithmic import protocol_buffers as pb
from async_rithmic.exceptions import RithmicErrorResponse

FakeResponse = namedtuple("FakeResponse", ["template_id", "account_id"])

class FakePlant:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.logger = MagicMock(
            info=print,
            error=print,
            exception=print,
            warning=print,
            debug=print,
        )

    async def _send_request(self, **kwargs):
        # Simulate network send latency
        await asyncio.sleep(random.uniform(0.001, 0.01))


class TestRequestManager:

    @pytest.fixture
    def plant(self):
        return FakePlant()

    @pytest.fixture
    def manager(self, plant):
        return RequestManager(plant)

    async def _simulate_realistic_responses(self, manager, request_id, template_id, account_id, total_messages):
        partials = total_messages

        for _ in range(partials):
            await asyncio.sleep(random.uniform(0.001, 0.02))  # jitter
            resp = FakeResponse(template_id + 1, account_id)
            manager.handle_response(resp)

        manager.mark_complete(request_id)

    async def test_heavy_interleaved_request_streams(self, manager):
        num_requests = 5
        accounts = [f"acct{i % 3}" for i in range(num_requests)]  # Shared among 3 accounts

        tasks = []

        for i in range(num_requests):
            template_id = random.randint(1000, 5000)
            account_id = accounts[i]
            total_messages = random.randint(3, 7)
            request_id = str(uuid.uuid4())

            task = asyncio.create_task(
                manager.send_and_collect(
                    user_msg=request_id,
                    template_id=template_id,
                    expected_response={"template_id": template_id + 1, "account_id": account_id},
                    account_id=account_id,
                )
            )
            tasks.append((task, request_id, template_id + 1, account_id, total_messages))

            await asyncio.sleep(0.5)

            asyncio.create_task(
                self._simulate_realistic_responses(manager, request_id, template_id, account_id, total_messages)
            )

        results = await asyncio.gather(*[t[0] for t in tasks])

        for i, (responses, (_, request_id, expected_template_id, account_id, expected_count)) in enumerate(zip(results, tasks)):
            assert len(responses) == expected_count, \
                f"[Request {request_id}] Expected {expected_count} responses, got {len(responses)}"

            for r in responses:
                assert r.template_id == expected_template_id, \
                    f"[Request {i}] Response had wrong template_id: {r.template_id} ≠ {expected_template_id}"
                assert r.account_id == account_id, \
                    f"[Request {i}] Response had wrong account_id: {r.account_id} ≠ {account_id}"

    async def test_no_response_times_out(self, manager):
        request_id = str(uuid.uuid4())
        with pytest.raises(asyncio.TimeoutError):
            await manager.send_and_collect(
                timeout=0.01,
                user_msg=request_id,
                template_id=312,
                expected_response=dict(template_id=313, user_msg=[request_id]),
            )

    async def test_error_reaches_caller(self):
        client = SimpleNamespace(
            retry_settings=SimpleNamespace(
                max_retries=1, timeout=1, jitter_range=None
            ),
            credentials={},
        )
        plant = OrderPlant(client)
        plant._send_request = AsyncMock()

        waiter = asyncio.create_task(
            plant._send_and_collect(
                template_id=316,
                account_id=None,
                expected_response={"template_id": 317},
            )
        )
        await asyncio.sleep(0)
        request_id = next(iter(plant.request_manager.done_events))

        response = pb.response_cancel_order_pb2.ResponseCancelOrder(
            template_id=317,
            user_msg=[request_id],
            rp_code=["1"],
        )
        await plant._process_response(response)

        with pytest.raises(RithmicErrorResponse):
            await waiter

    async def test_successful_cancel_response_remains_an_acknowledgement(self):
        client = SimpleNamespace(
            retry_settings=SimpleNamespace(
                max_retries=1, timeout=1, jitter_range=None
            ),
            credentials={},
        )
        plant = OrderPlant(client)
        plant._send_request = AsyncMock()

        waiter = asyncio.create_task(
            plant._send_and_collect(
                template_id=316,
                account_id=None,
                expected_response={"template_id": 317},
            )
        )
        await asyncio.sleep(0)
        request_id = next(iter(plant.request_manager.done_events))

        response = pb.response_cancel_order_pb2.ResponseCancelOrder(
            template_id=317,
            user_msg=[request_id],
            rp_code=["0"],
            basket_id="broker-order",
        )
        await plant._process_response(response)

        result = await waiter
        assert result == [response]

    async def test_errors_complete_only_the_matching_caller(self, manager):
        first = asyncio.create_task(
            manager.send_and_collect(
                user_msg="first",
                template_id=316,
                expected_response={"template_id": 317},
            )
        )
        second = asyncio.create_task(
            manager.send_and_collect(
                user_msg="second",
                template_id=316,
                expected_response={"template_id": 317},
            )
        )
        while set(manager.done_events) != {"first", "second"}:
            await asyncio.sleep(0)

        first_error = RithmicErrorResponse("first rejected")
        manager.mark_error("first", first_error)
        manager.mark_complete("second")

        with pytest.raises(RithmicErrorResponse) as caught:
            await first
        assert caught.value is first_error
        assert await second == []

        assert not manager.requests
        assert not manager.responses
        assert not manager.errors
        assert not manager.expected_responses
        assert not manager.done_events
        assert not manager.start_times

    async def test_send_failure_cleans_up_request(self, manager, plant):
        request_id = str(uuid.uuid4())
        send_error = RuntimeError("send failed")
        plant._send_request = AsyncMock(side_effect=send_error)

        with pytest.raises(RuntimeError, match="send failed"):
            await manager.send_and_collect(
                user_msg=request_id,
                template_id=312,
                expected_response=dict(template_id=313, user_msg=[request_id]),
            )

        assert not manager.requests
        assert not manager.responses
        assert not manager.errors
        assert not manager.expected_responses
        assert not manager.done_events
        assert not manager.start_times

    async def test_cancelled_request_cleans_up_request(self, manager, plant):
        request_id = str(uuid.uuid4())
        plant._send_request = AsyncMock()

        task = asyncio.create_task(manager.send_and_collect(
            user_msg=request_id,
            template_id=312,
            expected_response=dict(template_id=313, user_msg=[request_id]),
        ))
        await asyncio.sleep(0)

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert not manager.requests
        assert not manager.responses
        assert not manager.errors
        assert not manager.expected_responses
        assert not manager.done_events
        assert not manager.start_times
