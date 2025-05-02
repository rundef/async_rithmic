import pytest
import asyncio
import uuid
import random
from collections import namedtuple
from unittest.mock import MagicMock

from async_rithmic.helpers.request_manager import RequestManager

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


@pytest.mark.asyncio
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
