from datetime import datetime
import asyncio
from collections import defaultdict

from .base import BasePlant
from ..enums import SysInfraType, TimeBarType
from .. import protocol_buffers as pb

class HistoryPlant(BasePlant):
    infra_type = SysInfraType.HISTORY_PLANT

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.historical_tick_data = defaultdict(list)
        self.historical_time_bar_data = defaultdict(list)

        # Per-request events keyed by f"{symbol}" (tick) or f"{symbol}_{type}" (time bar).
        # Fixes two races in the prior single-shared-event design:
        #   1) Empty response: is_last_bar marker sets the event before any data
        #      callbacks fire, so pop(key) raised KeyError (fixed here with per-key
        #      events + .pop default).
        #   2) Concurrent requests: a second caller would overwrite the shared event,
        #      causing the first response to wake the second caller prematurely.
        self.historical_tick_events: dict = {}
        self.historical_time_bar_events: dict = {}

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
        key = f"{data['symbol']}_{data['type']}"
        self.historical_time_bar_data[key].append(data)

    async def _on_historical_tick(self, data):
        key = f"{data['symbol']}"
        self.historical_tick_data[key].append(data)

    async def get_historical_tick_data(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime,
        wait: bool = True
    ):
        """
        Creates and sends request for download of tick data for security/exchange over time period

        :param request_id: (str) generated request id used for processing as messages come in
        :param symbol: (str) valid security code (e.g. ES)
        :param exchange: (str) valid exchange code (e.g. CME)
        :param start_time: (dt) start time as datetime in utc
        :param end_time: (dt) end time as datetime in utc
        """
        key = f"{symbol}"

        if wait:
            event = asyncio.Event()
            self.historical_tick_events[key] = event

        await self._send_and_recv_immediate(
            template_id=206,
            user_msg=symbol,
            symbol=symbol,
            exchange=exchange,
            bar_type=pb.request_tick_bar_replay_pb2.RequestTickBarReplay.BarType.TICK_BAR,
            bar_type_specifier="1",
            bar_sub_type=pb.request_tick_bar_replay_pb2.RequestTickBarReplay.BarSubType.REGULAR,
            time_order=pb.request_tick_bar_replay_pb2.RequestTickBarReplay.TimeOrder.FORWARDS,
            start_index=self._datetime_to_index(start_time),
            finish_index=self._datetime_to_index(end_time),
        )

        # Wait until all the historical data has been fetched before returning it
        if wait:
            try:
                await asyncio.wait_for(event.wait(), 5.0)
            except asyncio.TimeoutError:
                # No response within 5s — return whatever accumulated (may be empty)
                pass
            finally:
                self.historical_tick_events.pop(key, None)

            return self.historical_tick_data.pop(key, [])

    async def get_historical_time_bars(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime,
        bar_type: TimeBarType,
        bar_type_periods: int,
        wait: bool = True
    ):
        key = f"{symbol}_{bar_type}"

        if wait:
            event = asyncio.Event()
            self.historical_time_bar_events[key] = event

        await self._send_and_recv_immediate(
            template_id=202,
            symbol=symbol,
            exchange=exchange,
            bar_type=bar_type,
            bar_type_period=bar_type_periods,
            time_order=pb.request_time_bar_replay_pb2.RequestTimeBarReplay.TimeOrder.FORWARDS,
            start_index=self._datetime_to_index(start_time),
            finish_index=self._datetime_to_index(end_time),
        )

        # Wait until all the historical data has been fetched before returning it
        if wait:
            try:
                await asyncio.wait_for(event.wait(), 5.0)
            except asyncio.TimeoutError:
                # No response within 5s — return whatever accumulated (may be empty)
                pass
            finally:
                self.historical_time_bar_events.pop(key, None)

            return self.historical_time_bar_data.pop(key, [])

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
            if is_last_bar:
                # Signal the specific per-request event (keyed by symbol+type).
                # Falls back to no-op if no waiter registered (defensive).
                key = f"{response.symbol}_{response.type}"
                event = self.historical_time_bar_events.get(key)
                if event is not None:
                    event.set()
                return

            data = self._response_to_dict(response)
            data["bar_end_datetime"] = datetime.fromtimestamp(data['marker'])

            await self.client.on_historical_time_bar.call_async(data)

        elif response.template_id == 207:
            # Historical tick bar
            is_last_bar = response.rp_code == ['0'] or response.rq_handler_rp_code == []
            if is_last_bar:
                key = f"{response.symbol}"
                event = self.historical_tick_events.get(key)
                if event is not None:
                    event.set()
                return

            data = self._response_to_dict(response)
            data["datetime"] = self._ssboe_usecs_to_datetime(response.data_bar_ssboe[0], response.data_bar_usecs[0])

            await self.client.on_historical_tick.call_async(data)

        elif response.template_id == 250:
            # Time Bar
            data = self._response_to_dict(response)
            data["bar_end_datetime"] = datetime.fromtimestamp(data['marker'])

            await self.client.on_time_bar.call_async(data)

        else:
            self.logger.warning(f"Unhandled inbound message with template_id={response.template_id}")
