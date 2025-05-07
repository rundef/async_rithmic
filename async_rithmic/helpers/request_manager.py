import asyncio
import time
from collections import defaultdict


class RequestManager:
    """
    Manages request-response streams where a single request may produce multiple responses.
    """

    def __init__(self, plant):
        self.plant = plant
        self.requests = {}
        self.responses = defaultdict(list)
        self.expected_responses = {}
        self.done_events = {}
        self.start_times = {}

    def start(self, request_id: str, request: dict, expected_response: dict):
        self.requests[request_id] = request
        self.responses[request_id] = []
        self.done_events[request_id] = asyncio.Event()
        self.expected_responses[request_id] = expected_response
        self.start_times[request_id] = time.time()

    async def send_and_collect(self, timeout: float = 30.0, **kwargs):
        """
        Sends a message and waits for all responses tied to the given request_id.
        """

        request_id = kwargs.get("user_msg")

        expected_response = kwargs.pop("expected_response")

        if kwargs["template_id"] in [312, 330]:
            # For new orders endpoints, the response will contain the same user_tag as the request
            # user_tag = the custom order id
            expected_response["user_tag"] = kwargs["user_tag"]

        elif "account_id" in kwargs:
            # Else, it will contain the same account id as the request
            expected_response["account_id"] = kwargs["account_id"]

        async with self.plant.lock:
            self.plant.logger.debug(f"Sending request {request_id}")

            self.start(request_id, kwargs, expected_response)

            await self.plant._send_request(**kwargs)

        try:
            await asyncio.wait_for(self.done_events[request_id].wait(), timeout=timeout)

        except asyncio.TimeoutError:
            self.plant.logger.exception(f"Timeout waiting for complete response stream for request_id={request_id}")
            self.done_events.pop(request_id, None)
            self.expected_responses.pop(request_id, None)
            raise

        finally:
            self.done_events.pop(request_id, None)

        return self.responses.pop(request_id, [])

    def handle_response(self, response):
        """
        Accumulate responses until the response stream is marked as complete
        """
        for request_id, expected_response in self.expected_responses.items():
            if not all(getattr(response, k) == v for k, v in expected_response.items()):
                continue

            self.responses[request_id].append(response)
            return True

    def mark_complete(self, request_id: str):
        """
        Marks the response stream for request_id as complete.
        """
        if request_id in self.done_events:
            elapsed = time.time() - self.start_times[request_id]
            num_responses = len(self.responses[request_id])

            self.plant.logger.debug(
                f"Completed request {request_id} "
                f"in {elapsed * 1000:.2f} ms with {num_responses} response(s)"
            )

            self.done_events[request_id].set()

            # Clean up
            self.requests.pop(request_id, None)
            self.done_events.pop(request_id, None)
            self.expected_responses.pop(request_id, None)
            self.start_times.pop(request_id, None)
        else:
            self.plant.logger.error(f"Unknown request {request_id}")

    def has_pending(self, request_id: str):
        return request_id in self.responses
