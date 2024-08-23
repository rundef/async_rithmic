import asyncio
import logging
from typing import Dict, Union

from pandas import DataFrame

from rithmic.config.credentials import RithmicEnvironment
from rithmic.interfaces.base import RithmicBaseApi, SHARED_RESPONSE_MAP
from rithmic.callbacks.callbacks import CallbackManager, CallbackId
from rithmic.protocol_buffers import request_login_pb2, last_trade_pb2, request_market_data_update_pb2, \
    request_front_month_contract_pb2
from rithmic.protocol_buffers.last_trade_pb2 import LastTrade
from rithmic.protocol_buffers.best_bid_offer_pb2 import BestBidOffer
from rithmic.protocol_buffers.response_front_month_contract_pb2 import ResponseFrontMonthContract
from rithmic.tools.general import dict_destructure, set_index_no_name
from rithmic.tools.meta import ApiType
from rithmic.tools.pyrithmic_exceptions import WebsocketClosedException, MissingCustomCallback
from rithmic.tools.pyrithmic_logger import logger, configure_logging

# Mapping of Template ID to the proto to use and the internal method used to process this message type
CONSUMPTION_RESPONSE_MAP = {
    150: dict(proto=LastTrade, fn='process_last_trade'),
    151: dict(proto=BestBidOffer, fn='process_best_bid_offer'),
    114: dict(proto=ResponseFrontMonthContract, fn='process_front_month_response')
}
CONSUMPTION_RESPONSE_MAP.update(SHARED_RESPONSE_MAP)


class TickDataStream:
    """
    Tick Data Stream records incoming tick data and state for a given security/exchange code registered for
    streaming tick data
    """
    def __init__(self, security_code: str, exchange_code: str):
        """
        Tick Data Stream init method

        :param security_code: (str) valid security code
        :param exchange_code: (str) valid exchange code
        """
        self.security_code = security_code
        self.exchange_code = exchange_code
        self.streamed_data = []
        self._last_row_processed = -1 # Used for periodic syncing
        self.is_streaming = True

    def stop_streaming(self) -> None:
        """
        Mark the stream as having stopped

        :return: None
        """
        self.is_streaming = False

    @property
    def tick_dataframe(self) -> DataFrame:
        """
        Pandas DataFrame representation of tick data streamed so far

        :return: (DataFrame)

        Columns and dtypes:
        timestamp        datetime64[ns, UTC]
        security_code                 object
        exchange_code                 object
        close                        float64
        volume                         int64
        bid_volume                     int64
        ask_volume                     int64
        """
        data = self.streamed_data[:]
        df = DataFrame(data)
        if len(df) > 0:
            df = set_index_no_name(df, 'timestamp')
        return df

    @property
    def tick_count(self) -> int:
        """
        Ticks streamed so far

        :return: (int) number of ticks
        """
        return len(self.streamed_data)

    @property
    def stream_key(self) -> tuple:
        """
        Key for use in mapping, streams should be unique for a given security/exchange combination

        :return: (tuple) of security code and exchange code
        """
        return self.security_code, self.exchange_code

    def add_new_tick_data(self, data: dict) -> None:
        """
        Add incoming new tick data to the stream

        :param data: (dict) new tick data
        :return: None
        """
        self.streamed_data.append(data)

    def _set_last_row_processed(self, n: int) -> None:
        """
        Used for managing periodic syncing so only new data is sent at each iteration

        :param n: (int) row number that has already been sent for processing in registered callback
        :return: None
        """
        self._last_row_processed = n


class RithmicTickerApi(RithmicBaseApi):
    """
    Rithmic Ticker API For the TICKER PLANT to stream live tick data
    """
    infra_type = request_login_pb2.RequestLogin.SysInfraType.TICKER_PLANT
    api_type = ApiType.TICKER

    def __init__(self, env: RithmicEnvironment = None, callback_manager: CallbackManager = None,
                 auto_connect: bool = True, loop=None, periodic_sync_interval_seconds: float = 0.1):
        """
        Rithmic Ticker API init method

        :param env: (RithmicEnvironment) provide a rithmic environment to connect to, if omitted, tries to get the
                    default environment from the Environment Variable RITHMIC_ENVIRONMENT_NAME
        :param callback_manager: (CallbackManager) provide a configured manager with callbacks registered
        :param auto_connect: (bool) automatically connect and log into Rithmic, defaults to True
        :param loop: (AbstractEventLoop) asyncio event loop can be provided to share/use existing loop
        :param periodic_sync_interval_seconds: (float) seconds between the periodic sync callback for rows of new tick
                                                data
        """
        self.consuming_subscription = False
        RithmicBaseApi.__init__(self, env, callback_manager, auto_connect, loop)
        self.tick_data_streams: Dict[tuple, TickDataStream] = dict()
        self.periodic_sync_interval_seconds = None
        self._set_periodic_sync_interval(periodic_sync_interval_seconds)
        self.underlying_front_month = dict()

    def connect_and_login(self) -> None:
        """
        Connects and logs into Rithmic and starts message subscription

        :return: None
        """
        super(RithmicTickerApi, self).connect_and_login()
        if self.consuming_subscription is False:
            asyncio.run_coroutine_threadsafe(self._consume_subscription(), loop=self.loop)

    @property
    def total_tick_count(self) -> int:
        """
        Total number of ticks streamed across all streams
        :return: (int) Total number of ticks
        """
        return sum(stream.tick_count for stream in self.tick_data_streams.values())

    @property
    def streams_consuming_count(self) -> int:
        """
        Number of streams currently subscribed for streaming
        :return: (int)
        """
        return len(self.tick_data_streams)

    def _add_tick_data_stream(self, stream: TickDataStream) -> None:
        """
        Internally map a stream for ongoing management

        :param stream: (TickDataStream) stream object to map
        :return: None
        """
        self.tick_data_streams[stream.stream_key] = stream

    def _get_stream_by_security_exchange(self, security_code: str, exchange_code: str) -> TickDataStream:
        """
        Get the stream registered for a given security/exchange combination.
        Used to get the stream as a new tick comes in to record and for stopping a stream from continuing

        :param security_code: (str) valid security code already registered
        :param exchange_code: (str) valid exchange code already registered
        :return: (TickDataStream) the registered stream
        """
        return self.tick_data_streams[(security_code, exchange_code)]

    def _set_periodic_sync_interval(self, seconds: float):
        """
        Sets the interval for periodic syncing and starts the processing callback if registered

        :param seconds: (float) number of seconds between processing new data
        :return:
        """
        self.periodic_sync_interval_seconds = seconds
        self._register_periodic_sync()

    def _register_periodic_sync(self) -> None:
        """
        Starts the periodic syncing callback for asynchronous processing
        :return: None
        """
        has_sync_callback = self.callback_manager.get_callback_by_callback_id(
            CallbackId.TICKER_PERIODIC_LIVE_TICK_DATA_SYNCING)
        if has_sync_callback:
            asyncio.run_coroutine_threadsafe(self.periodic_syncing(), loop=self.loop)

    async def _consume_subscription(self) -> None:
        """
        Consumes new messages as data is streamed, sends a heartbeat if no data received after 5 seconds and
        the websocket is still open. Starts once api is connected and logged in.

        :return: None
        """
        connected = True
        self.consuming_subscription = True
        await self.send_heartbeat()
        while connected:
            msg_buf = bytearray()
            waiting_for_msg = True
            while waiting_for_msg:
                try:
                    logger.debug('Waiting for msg...')
                    msg_buf = await asyncio.wait_for(self.recv_buffer(), timeout=5)
                    waiting_for_msg = False
                except asyncio.TimeoutError:
                    if self.ws.open:
                        await self.send_heartbeat()
                    else:
                        logger.info("connection appears to be closed.  exiting consume()")
                        raise WebsocketClosedException('Websocket has closed')
            template_id = self.get_template_id_from_message_buffer(msg_buf)
            if template_id == 19:
                continue
            if template_id == 13:
                connected = False
                continue
            else:
                self._process_new_message(template_id, msg_buf)

    def _process_new_message(self, template_id: int, msg_buf):
        """
        Processes messages and routes based on template id

        :param template_id: (int) template id of the message
        :param msg_buf: (bytes) message received in bytes
        :return:
        """
        print("_process_new_message", template_id)
        if template_id in CONSUMPTION_RESPONSE_MAP:
            meta = CONSUMPTION_RESPONSE_MAP[template_id]
            msg = meta['proto']()
            msg.ParseFromString(msg_buf[4:])
            fn = getattr(self, meta['fn'])
            result = fn(template_id, msg)
            callback_fn = self.callback_manager.get_callback_by_template_id(CallbackId.TICKER_LAST_TRADE)
            if callback_fn is not None and result is not None:
                self.perform_callback(callback_fn, [result])

    def process_last_trade(self, template_id: int, msg: LastTrade):
        """
        Processes new tick data message as it streams in. Will add new data to the streamed_data and perform
        callback if custom callback provided

        :param template_id: (int) template id of the message received over the websocket
        :param msg: (LastTrade) protocol buffer message
        :return: (dict) dictionary of last trade data
        """
        data = self._get_row_information(template_id, msg)
        from datetime import datetime
        print("HELLO", datetime.now(), data)
        if msg.trade_size == 0:
            return
        if data['aggressor'] == 1:
            bid_volume, ask_volume = 0, data['trade_size']
        else:
            ask_volume, bid_volume = 0, data['trade_size']
        keys = ['update_time', 'symbol', 'exchange', 'trade_price', 'trade_size']
        timestamp, security_code, exchange_code, close, volume = dict_destructure(data, keys)
        result = dict(
            timestamp=timestamp, security_code=security_code, exchange_code=exchange_code, close=close, volume=volume,
            bid_volume=bid_volume, ask_volume=ask_volume
        )
        self.process_new_tick_data(result, security_code, exchange_code)
        return result

    def process_best_bid_offset(self, template_id: int, msg: BestBidOffer):
        print(type(msg))
        data = self._get_row_information(template_id, msg)
        from datetime import datetime
        print("BIDOFFSET", datetime.now(), data)

    def process_front_month_response(self, template_id: int, msg: ResponseFrontMonthContract):
        """
        Handles response from a front month request for a given underlying

        :param template_id: (int) template id of the message
        :param msg: (ResponseFrontMonthContract) response from the server
        :return:
        """
        if msg.rp_code[0] == '0': # Good response
            self.underlying_front_month[msg.symbol] = msg.trading_symbol
        else:
            requested_underlying = msg.user_msg[0]
            self.underlying_front_month[requested_underlying] = None

    async def periodic_syncing(self):
        """
        Subscribe to periodic syncing if a custom callback is provided to handle new data every n seconds.
        Can be used to periodically process chunks of tick data, eg save new records to database every 0.1 seconds.
        Processes each stream separately for a given security_code/exchange_code

        :return: None
        """
        callback_fn = self.callback_manager.get_callback_by_callback_id(
            CallbackId.TICKER_PERIODIC_LIVE_TICK_DATA_SYNCING
        )
        if callback_fn is None:
            msg = 'Custom callback for period syncing required, use attach_periodic_sync_callback to set first'
            raise MissingCustomCallback(msg)
        complete = False
        while not complete:
            if self.total_tick_count > 0:
                for stream in self.tick_data_streams.values():
                    df_current = stream.tick_dataframe
                    df = df_current.iloc[stream._last_row_processed:]
                    if len(df) > 0:
                        self.perform_callback(callback_fn, [df, stream.security_code, stream.exchange_code])
                        stream._set_last_row_processed(len(df_current))
            await asyncio.sleep(self.periodic_sync_interval_seconds)

    def process_new_tick_data(self, data, security_code, exchange_code):
        """
        New tick row is appended to the individual stream
        :param data: dict of tick data
        :return: None
        """
        stream = self._get_stream_by_security_exchange(security_code, exchange_code)
        stream.add_new_tick_data(data)

    def _create_subscribe_unsubscribe_request(self, security_code, exchange_code, subscribe: bool = True):
        """
        Create a request for subscription to or unsubcription from streaming tick data for a security/exchange
        combination

        :param security_code: (str) valid security code
        :param exchange_code: (str) valid exchange code
        :param subscribe: (bool) True to subscribe, False to unsubscribe
        :return:
        """
        rq = request_market_data_update_pb2.RequestMarketDataUpdate()
        rq.template_id = 100
        msg = 'subscribing' if subscribe else 'unsubscribing'
        request_type = 'SUBSCRIBE' if subscribe else 'UNSUBSCRIBE'
        rq.user_msg.append(msg)
        rq.symbol = security_code
        rq.exchange = exchange_code
        rq.request = getattr(request_market_data_update_pb2.RequestMarketDataUpdate.Request, request_type)
        last_trade = request_market_data_update_pb2.RequestMarketDataUpdate.UpdateBits.LAST_TRADE
        rq.update_bits = last_trade
        buf = self._convert_request_to_bytes(rq)
        return buf

    async def _subscribe_to_market_data_stream(self, security_code: str, exchange_code: str):
        """
        Creates request and sends to subscribe for a tick data stream

        :param security_code: (str) valid security code
        :param exchange_code: (str) valid exchange code
        :return:
        """
        buffer = self._create_subscribe_unsubscribe_request(security_code, exchange_code, subscribe=True)
        await self.send_buffer(buffer)
        logger.info(f'Subscribed to Market Data for {security_code} on {exchange_code}')

    async def _unsubscribe_from_market_data_stream(self, security_code, exchange_code):
        """
        Creates request and sends to unsubscribe for a tick data stream

        :param security_code: (str) valid security code
        :param exchange_code: (str) valid exchange code
        :return:
        """
        buffer = self._create_subscribe_unsubscribe_request(security_code, exchange_code, subscribe=False)
        await self.send_buffer(buffer)
        logger.info(f'Unsubscribed to Market Data for {security_code} on {exchange_code}')

    def stream_market_data(self, security_code: str, exchange_code: str) -> TickDataStream:
        """
        Subscribe to a tick data streaming for a security_code and exchange_code combination, eg ESU3 and CME

        :param security_code: (str) valid security code
        :param exchange_code: (str) valid exchange code
        :return: (TickDataStream) stream object that captures new tick data row by row
        """
        stream = TickDataStream(security_code, exchange_code)
        self._add_tick_data_stream(stream)
        asyncio.run_coroutine_threadsafe(
            self._subscribe_to_market_data_stream(security_code, exchange_code), loop=self.loop
        )
        return stream

    def stop_market_data_stream(self, security_code: str, exchange_code: str) -> None:
        """
        Unsubscribe tick data streaming for a security_code and exchange_code combination, eg ESU3 and CME

        :param security_code: (str) valid security code
        :param exchange_code: (str) valid exchange code
        :return: None
        """
        stream = self._get_stream_by_security_exchange(security_code, exchange_code)
        stream.stop_streaming()
        if self.consuming_subscription is False:
            return
        asyncio.run_coroutine_threadsafe(
            self._unsubscribe_from_market_data_stream(security_code, exchange_code), loop=self.loop
        )

    async def _request_front_month_contract(self, underlying_code: str, exchange_code: str) -> Union[str, None]:
        """
        Create request for front month contract of a given underlying/exchange combination

        :param underlying_code: (str) valid underlying code
        :param exchange_code: (str) valid exchange code
        :return: (str) the front month futures contract
        """
        rq = request_front_month_contract_pb2.RequestFrontMonthContract()

        rq.template_id = 113
        rq.symbol = underlying_code
        rq.exchange = exchange_code
        rq.user_msg.append(underlying_code)
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)
        while underlying_code not in self.underlying_front_month:
            await asyncio.sleep(0.01)
        return self.underlying_front_month[underlying_code]

    def get_front_month_contract(self, underlying_code: str, exchange_code: str) -> Union[str, None]:
        """
        Get the current Front Month Contract of an underlying code and exchange, eg ES and CME
        :param underlying_code: (str) valid underlying code
        :param exchange_code: (str) valid exchange code
        :return: (str) the front month futures contract
        """
        security_code = asyncio.run_coroutine_threadsafe(
            self._request_front_month_contract(underlying_code, exchange_code), loop=self.loop
        ).result()
        return security_code
