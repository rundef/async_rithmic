from datetime import datetime
import asyncio
from dataclasses import dataclass

from .base import BasePlant
from ..exceptions import HistoricalDataRequestInProgressError
from ..enums import SysInfraType, TimeBarType
from .. import protocol_buffers as pb


@dataclass
class HistoricalDataRequest:
    """
    Tracks one in-flight historical data request.
    """

    # Request time range
    start_index: int
    end_index: int

    # Request params
    params: dict

    # Pagination
    page_count: int
    max_pages: int

    # State
    done: asyncio.Event
    data_received: asyncio.Event
    data: list[dict]

    last_marker: int = 0

    @property
    def reached_max_pages(self) -> bool:
        return self.page_count >= self.max_pages

    @property
    def received_no_data(self) -> bool:
        return self.last_marker == 0

    @property
    def reached_end(self) -> bool:
        return self.last_marker >= self.end_index

    @property
    def is_finished_downloading(self) -> bool:
        return self.reached_max_pages or self.received_no_data or self.reached_end

class HistoryPlant(BasePlant):
    infra_type = SysInfraType.HISTORY_PLANT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.historical_time_bar_requests = {}
        self.historical_tick_requests = {}

        self.client.on_historical_tick += self._on_historical_tick
        self.client.on_historical_time_bar += self._on_historical_time_bar

    async def _login(self):
        await super()._login()

        for symbol, exchange, bar_type, bar_type_periods in self._subscriptions["time_bar"]:
            await self.subscribe_to_time_bar_data(symbol, exchange, bar_type, bar_type_periods)

    def _datetime_to_index(self, dt: datetime):
        dt = self._datetime_to_utc(dt)
        return int(dt.timestamp())

    async def _on_historical_time_bar(self, data):
        key = data["_key"]
        if (request := self.historical_time_bar_requests.get(key)) is not None:
            request.data.append(data)
            request.data_received.set()

    async def _on_historical_tick(self, data):
        key = data["_key"]
        if (request := self.historical_tick_requests.get(key)) is not None:
            request.data.append(data)
            request.data_received.set()

    async def _wait_for_historical_request_completion(
        self,
        request: HistoricalDataRequest,
        idle_timeout: float,
    ) -> list[dict]:
        """
        Waits for historical data request to complete
        Raises TimeoutError exception if no new data has been received in the last `idle_timeout` seconds
        """
        while not request.done.is_set():
            request.data_received.clear()

            done_task = asyncio.create_task(request.done.wait())
            data_task = asyncio.create_task(request.data_received.wait())

            try:
                done, pending = await asyncio.wait(
                    {done_task, data_task},
                    timeout=idle_timeout,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                for task in pending:
                    task.cancel()

                if not done:
                    raise TimeoutError(
                        f"Historical data request stalled: no data or completion message "
                        f"received for {idle_timeout:.1f}s"
                    )

                if done_task in done:
                    break

            finally:
                for task in (done_task, data_task):
                    if not task.done():
                        task.cancel()

        return request.data

    async def get_historical_tick_data(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime,
        wait: bool = True,
        idle_timeout: float = 5.0,
    ):
        """
        Requests historical ticks for a symbol/exchange over a time range.

        :param symbol: Security code, e.g. "NQM6".
        :param exchange: Exchange code, e.g. "CME".
        :param start_time: Start time of the replay request.
        :param end_time: End time of the replay request.
        :param wait: If True, wait for the historical replay to complete and return
            the collected ticks. If False, return immediately after sending the
            request; ticks are still emitted through the ``on_historical_tick``
            callback.
        :param idle_timeout: Maximum number of seconds to wait without receiving
            either a historical bar or the replay completion message. This is an
            idle/stall timeout, not a total request timeout; the timer resets every
            time progress is observed.
        :return: A list of historical tick dictionaries when ``wait=True``;
            otherwise ``None``.
        :raises HistoricalDataRequestInProgressError: If another historical tick
            request is already in progress.
        :raises TimeoutError: If no bar or completion message is received for
            ``idle_timeout`` seconds while waiting.
        """

        key = f"{symbol}_{exchange}"

        if key in self.historical_tick_requests:
            raise HistoricalDataRequestInProgressError(
                "Cannot start another historical tick request with the same "
                "symbol and exchange while one is already in progress."
            )

        self.historical_tick_requests[key] = HistoricalDataRequest(
            done=asyncio.Event(),
            data_received=asyncio.Event(),
            data=[]
        )

        await self._send_request(
            template_id=206,
            user_msg=key,
            symbol=symbol,
            exchange=exchange,
            bar_type=pb.request_tick_bar_replay_pb2.RequestTickBarReplay.BarType.TICK_BAR,
            bar_type_specifier="1",
            bar_sub_type=pb.request_tick_bar_replay_pb2.RequestTickBarReplay.BarSubType.REGULAR,
            time_order=pb.request_tick_bar_replay_pb2.RequestTickBarReplay.TimeOrder.FORWARDS,
            start_index=self._datetime_to_index(start_time),
            finish_index=self._datetime_to_index(end_time),
        )

        if not wait:
            # Historical ticks will still be emitted through `on_historical_tick`,
            # but this call returns immediately instead of collecting them.
            return None

        # Wait until Rithmic sends the completion message, and return ticks.
        try:
            return await self._wait_for_historical_request_completion(
                request=self.historical_tick_requests[key],
                idle_timeout=idle_timeout,
            )
        finally:
            self.historical_tick_requests.pop(key, None)

    async def get_historical_time_bars(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime,
        bar_type: TimeBarType,
        bar_type_periods: int,
        wait: bool = True,
        idle_timeout: float = 5.0,
        max_pages: int = 1_000,
    ):
        """
        Requests historical time bars for a symbol/exchange over a time range.

        :param symbol: Security code, e.g. "NQM6".
        :param exchange: Exchange code, e.g. "CME".
        :param start_time: Start time of the replay request.
        :param end_time: End time of the replay request.
        :param bar_type: Type of time bar to request.
        :param bar_type_periods: Bar period value. For minute bars, this is the
            number of minutes. For second bars, this is the number of seconds.
        :param wait: If True, wait for the historical replay to complete and return
            the collected bars. If False, return immediately after sending the
            request; bars are still emitted through the ``on_historical_time_bar``
            callback.
        :param idle_timeout: Maximum number of seconds to wait without receiving
            either a historical bar or the replay completion message. This is an
            idle/stall timeout, not a total request timeout; the timer resets every
            time progress is observed.
        :param max_pages: Maximum number of replay pages to request. Use `1` to send
            a single replay request without pagination. Values greater than `1` allow
            the client to issue additional replay requests until the returned bars cover
            the requested `end_time`. This handles Rithmic replay truncation.
        :return: A list of historical time bar dictionaries when ``wait=True``;
            otherwise ``None``.
        :raises HistoricalDataRequestInProgressError: If another historical time bar
            request is already in progress.
        :raises TimeoutError: If no bar or completion message is received for
            ``idle_timeout`` seconds while waiting.
        """

        key = f"{symbol}_{exchange}_{bar_type}_{bar_type_periods}"

        if key in self.historical_time_bar_requests:
            raise HistoricalDataRequestInProgressError(
                "Cannot start another historical time bar request with the same "
                "symbol, exchange, bar type, and period while one is already in progress."
            )

        start_index = self._datetime_to_index(start_time)
        end_index = self._datetime_to_index(end_time)

        self.historical_time_bar_requests[key] = HistoricalDataRequest(
            # Request range
            start_index=start_index,
            end_index=end_index,

            # Request param
            params=dict(
                symbol=symbol,
                exchange=exchange,
                bar_type=bar_type,
                bar_type_period=bar_type_periods,
                time_order=pb.request_time_bar_replay_pb2.RequestTimeBarReplay.TimeOrder.FORWARDS,
            ),

            # Pagination
            page_count=1,
            max_pages=max_pages,

            # State
            done=asyncio.Event(),
            data_received=asyncio.Event(),
            data=[],
        )

        await self._request_historical_time_bars(key)

        if not wait:
            # Historical bars will still be emitted through `on_historical_time_bar`,
            # but this call returns immediately instead of collecting them.
            return None

        # Wait until Rithmic sends the completion message, and return bars.
        try:
            return await self._wait_for_historical_request_completion(
                request=self.historical_time_bar_requests[key],
                idle_timeout=idle_timeout,
            )
        finally:
            self.historical_time_bar_requests.pop(key, None)

    async def _request_historical_time_bars(self, key: str):
        request: HistoricalDataRequest = self.historical_time_bar_requests[key]

        self.logger.debug(f"Requesting page {request.page_count} (start index = {request.start_index}) of historical time bars for {key}")

        await self._send_request(
            template_id=202,
            user_msg=key,
            start_index=request.start_index,
            finish_index=request.end_index,
            **request.params,
        )

    async def subscribe_to_time_bar_data(
        self,
        symbol: str,
        exchange: str,
        bar_type: TimeBarType,
        bar_type_periods: int
    ):
        """
        Subscribes to time bars
        """

        sub = (symbol, exchange, bar_type, bar_type_periods)
        self._subscriptions["time_bar"].add(sub)

        return await self._send_and_recv_immediate(
            template_id=200,
            symbol=symbol,
            exchange=exchange,
            request=pb.request_time_bar_update_pb2.RequestTimeBarUpdate.Request.SUBSCRIBE,
            bar_type=bar_type,
            bar_type_period=bar_type_periods,
        )

    async def unsubscribe_from_time_bar_data(
        self,
        symbol: str,
        exchange: str,
        bar_type: TimeBarType,
        bar_type_periods: int
    ):
        sub = (symbol, exchange, bar_type, bar_type_periods)
        self._subscriptions["time_bar"].discard(sub)

        return await self._send_and_recv_immediate(
            template_id=200,
            symbol=symbol,
            exchange=exchange,
            request=pb.request_time_bar_update_pb2.RequestTimeBarUpdate.Request.UNSUBSCRIBE,
            bar_type=bar_type,
            bar_type_period=bar_type_periods,
        )

    async def _process_response(self, response):
        if await super()._process_response(response):
            return True

        if response.template_id == 203:
            # Historical time bar
            is_last_bar = response.rp_code == ['0'] or response.rq_handler_rp_code == []
            key = response.user_msg[0]

            if is_last_bar:
                if (request := self.historical_time_bar_requests.get(key)) is not None:
                    if request.is_finished_downloading:
                        self.logger.debug(f"Finished downloading historical time bars for {key}")

                        self.historical_time_bar_requests[key].done.set()
                        self.historical_time_bar_requests.pop(key, None)

                    else:
                        # Request the next page of results
                        next_start_index = request.last_marker + 1
                        request.last_marker = 0
                        request.page_count += 1
                        request.start_index = next_start_index

                        await asyncio.sleep(0.01)
                        await self._request_historical_time_bars(key)

                return

            data = self._response_to_dict(response)
            data["_key"] = key
            data["bar_end_datetime"] = datetime.fromtimestamp(data['marker'])

            if (request := self.historical_time_bar_requests.get(key)) is not None:
                request.last_marker = data['marker']

            await self.client.on_historical_time_bar.call_async(data)

        elif response.template_id == 207:
            # Historical tick bar
            is_last_bar = response.rp_code == ['0'] or response.rq_handler_rp_code == []
            key = response.user_msg[0]

            if is_last_bar:
                if self.historical_tick_requests.get(key) is not None:
                    self.historical_tick_requests[key].done.set()
                    self.historical_tick_requests.pop(key, None)
                return

            data = self._response_to_dict(response)
            data["_key"] = key
            data["datetime"] = self._ssboe_usecs_to_datetime(response.data_bar_ssboe[0], response.data_bar_usecs[0])

            await self.client.on_historical_tick.call_async(data)

        elif response.template_id == 250:
            # Time Bar
            data = self._response_to_dict(response)
            data["bar_end_datetime"] = datetime.fromtimestamp(data['marker'])

            await self.client.on_time_bar.call_async(data)

        else:
            self.logger.warning(f"Unhandled inbound message with template_id={response.template_id}")
