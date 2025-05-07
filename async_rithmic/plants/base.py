import websockets
from websockets import ConnectionClosedOK
from websockets.protocol import OPEN
import asyncio
import time
import uuid
from datetime import datetime
import pytz
from tzlocal import get_localzone
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.json_format import MessageToDict

from .. import protocol_buffers as pb
from ..logger import logger
from ..exceptions import RithmicErrorResponse
from ..helpers.request_manager import RequestManager
from ..helpers.connectivity import DisconnectionHandler

TEMPLATES_MAP = {
    # Shared
    10: pb.request_login_pb2.RequestLogin,
    11: pb.response_login_pb2.ResponseLogin,
    12: pb.request_logout_pb2.RequestLogout,
    13: pb.response_logout_pb2.ResponseLogout,
    14: pb.request_reference_data_pb2.RequestReferenceData,
    15: pb.response_reference_data_pb2.ResponseReferenceData,
    16: pb.request_rithmic_system_info_pb2.RequestRithmicSystemInfo,
    17: pb.response_rithmic_system_info_pb2.ResponseRithmicSystemInfo,
    18: pb.request_heartbeat_pb2.RequestHeartbeat,
    19: pb.response_heartbeat_pb2.ResponseHeartbeat,

    # Market Data Infrastructure
    100: pb.request_market_data_update_pb2.RequestMarketDataUpdate,
    101: pb.response_market_data_update_pb2.ResponseMarketDataUpdate,
    109: pb.request_search_symbols_pb2.RequestSearchSymbols,
    110: pb.response_search_symbols_pb2.ResponseSearchSymbols,
    113: pb.request_front_month_contract_pb2.RequestFrontMonthContract,
    114: pb.response_front_month_contract_pb2.ResponseFrontMonthContract,

    #115: pb.request_depth_by_order_snapshot_pb2.RequestDepthByOrderSnapshot,
    #116: pb.response_depth_by_order_snapshot_pb2.ResponseDepthByOrderSnapshot,
    #117: pb.request_depth_by_order_updates_pb2.RequestDepthByOrderUpdates,
    #118: pb.response_depth_by_order_updates_pb2.ResponseDepthByOrderUpdates,

    150: pb.last_trade_pb2.LastTrade,
    151: pb.best_bid_offer_pb2.BestBidOffer,
    #156: pb.order_book_pb2.OrderBook,
    #160: pb.depth_by_order.DepthByOrder,
    #161: pb.depth_by_order_end_event.DepthByOrderEndEvent,

    # Order Plant Infrastructure
    300: pb.request_login_info_pb2.RequestLoginInfo,
    301: pb.response_login_info_pb2.ResponseLoginInfo,
    302: pb.request_account_list_pb2.RequestAccountList,
    303: pb.response_account_list_pb2.ResponseAccountList,
    304: pb.request_account_rms_info_pb2.RequestAccountRmsInfo,
    305: pb.response_account_rms_info_pb2.ResponseAccountRmsInfo,
    306: pb.request_product_rms_info_pb2.RequestProductRmsInfo,
    307: pb.response_product_rms_info_pb2.ResponseProductRmsInfo,
    308: pb.request_subscribe_for_order_updates_pb2.RequestSubscribeForOrderUpdates,
    309: pb.response_subscribe_for_order_updates_pb2.ResponseSubscribeForOrderUpdates,
    310: pb.request_trade_routes_pb2.RequestTradeRoutes,
    311: pb.response_trade_routes_pb2.ResponseTradeRoutes,
    312: pb.request_new_order_pb2.RequestNewOrder,
    313: pb.response_new_order_pb2.ResponseNewOrder,
    314: pb.request_modify_order_pb2.RequestModifyOrder,
    315: pb.response_modify_order_pb2.ResponseModifyOrder,
    316: pb.request_cancel_order_pb2.RequestCancelOrder,
    317: pb.response_cancel_order_pb2.ResponseCancelOrder,
    318: pb.request_show_order_history_dates_pb2.RequestShowOrderHistoryDates,
    319: pb.response_show_order_history_dates_pb2.ResponseShowOrderHistoryDates,
    320: pb.request_show_orders_pb2.RequestShowOrders,
    321: pb.response_show_orders_pb2.ResponseShowOrders,
    324: pb.request_show_order_history_summary_pb2.RequestShowOrderHistorySummary,
    325: pb.response_show_order_history_summary_pb2.ResponseShowOrderHistorySummary,
    330: pb.request_bracket_order_pb2.RequestBracketOrder,
    331: pb.response_bracket_order_pb2.ResponseBracketOrder,
    332: pb.request_update_target_bracket_level_pb2.RequestUpdateTargetBracketLevel,
    333: pb.response_update_target_bracket_level_pb2.ResponseUpdateTargetBracketLevel,
    334: pb.request_update_stop_bracket_level_pb2.RequestUpdateStopBracketLevel,
    335: pb.response_update_stop_bracket_level_pb2.ResponseUpdateStopBracketLevel,
    336: pb.request_subscribe_to_bracket_updates_pb2.RequestSubscribeToBracketUpdates,
    337: pb.response_subscribe_to_bracket_updates_pb2.ResponseSubscribeToBracketUpdates,

    350: pb.trade_route_pb2.TradeRoute,
    351: pb.rithmic_order_notification_pb2.RithmicOrderNotification,
    352: pb.exchange_order_notification_pb2.ExchangeOrderNotification,
    353: pb.bracket_updates_pb2.BracketUpdates,

    # History Plant Infrastructure
    200: pb.request_time_bar_update_pb2.RequestTimeBarUpdate,
    201: pb.response_time_bar_update_pb2.ResponseTimeBarUpdate,
    202: pb.request_time_bar_replay_pb2.RequestTimeBarReplay,
    203: pb.response_time_bar_replay_pb2.ResponseTimeBarReplay,
    204: pb.request_tick_bar_update_pb2.RequestTickBarUpdate,
    205: pb.response_tick_bar_update_pb2.ResponseTickBarUpdate,
    206: pb.request_tick_bar_replay_pb2.RequestTickBarReplay,
    207: pb.response_tick_bar_replay_pb2.ResponseTickBarReplay,
    250: pb.time_bar_pb2.TimeBar,
    251: pb.tick_bar_pb2.TickBar,

    # PnL Plant Infrastructure
    400: pb.request_pnl_position_updates_pb2.RequestPnLPositionUpdates,
    401: pb.response_pnl_position_updates_pb2.ResponsePnLPositionUpdates,
    402: pb.request_pnl_position_snapshot_pb2.RequestPnLPositionSnapshot,
    403: pb.response_pnl_position_snapshot_pb2.ResponsePnLPositionSnapshot,
    450: pb.instrument_pnl_position_update_pb2.InstrumentPnLPositionUpdate,
    451: pb.account_pnl_position_update_pb2.AccountPnLPositionUpdate,
}

class BasePlant:
    infra_type = None

    def __init__(self, client, listen_interval=0.1):
        self.ws = None
        self.client = client
        self.lock = asyncio.Lock()
        self.request_manager = RequestManager(self)

        # Heartbeats has to be sent every {interval} seconds, unless an update was received
        self.heartbeat_interval = None
        self.listen_interval = listen_interval
        self.last_message_time = None

        self.logger = logger.getChild(f"plant.{self.plant_type}")

    @property
    def is_connected(self) -> bool:
        return self.ws is not None and self.ws.state == OPEN

    @property
    def credentials(self):
        return self.client.credentials

    @property
    def ssl_context(self):
        return self.client.ssl_context

    @property
    def plant_type(self):
        return {
            pb.request_login_pb2.RequestLogin.SysInfraType.HISTORY_PLANT: "history",
            pb.request_login_pb2.RequestLogin.SysInfraType.PNL_PLANT: "pnl",
            pb.request_login_pb2.RequestLogin.SysInfraType.TICKER_PLANT: "ticker",
            pb.request_login_pb2.RequestLogin.SysInfraType.ORDER_PLANT: "order",
        }[self.infra_type]

    async def _connect(self):
        """
        Clients should follow the below sequence for communicating with protocol server,
        1. Open a websocket, upon connecting send 'RequestRithmicSystemInfo' message.
           Parse the response and record list of 'system names' available. Close this connection

        2. Open a new websocket, and login using the desired 'system_name'.
        """
        self.ws = await websockets.connect(
            self.credentials["gateway"],
            ssl=self.ssl_context,
            ping_interval=10
        )

        if self.plant_type == "ticker":
            info = await self.get_system_info()
            await self._disconnect()

            if self.credentials["system_name"] not in info.system_name:
                raise Exception(f"You must specify valid SYSTEM_NAME in the credentials: {info.system_name}")

            self.ws = await websockets.connect(
                self.credentials["gateway"],
                ssl=self.ssl_context,
                ping_interval=10
            )

    async def _disconnect(self):
        if self.is_connected:
            await self.ws.close(1000, "Closing Connection")

    async def _login(self):
        responses = await self._send_and_collect(
            template_id=10,
            expected_response=dict(template_id=11),
            account_id=None,
            template_version="3.9",
            user=self.credentials["user"],
            password=self.credentials["password"],
            system_name=self.credentials["system_name"],
            app_name=self.credentials["app_name"],
            app_version=self.credentials["app_version"],
            infra_type=self.infra_type,
        )
        response = self._first(responses)

        self.heartbeat_interval = response.heartbeat_interval

        # Upon making a successful login, clients are expected to send at least a heartbeat request to the server
        await self._send_heartbeat()

        return response

    async def _logout(self):
        try:
            async with self.lock:
                await self._send_request(template_id=12)

        except ConnectionClosedOK:
            pass

    async def get_system_info(self):
        return await self._send_and_recv(template_id=16)

    async def get_reference_data(self, symbol: str, exchange: str):
        responses = await self._send_and_collect(
            template_id=14,
            expected_response=dict(template_id=15),
            symbol=symbol,
            exchange=exchange,
            account_id=None
        )
        return self._first(responses)

    async def _send(self, message: bytes):
        await self.ws.send(message)

    async def _recv(self):
        buffer = await self.ws.recv()
        self.last_message_time = time.time()
        return buffer

    async def _send_request(self, **kwargs):
        """
        Create Request class instance, convert it to bytes and send it to the server
        """
        template_id = kwargs["template_id"]

        if template_id not in TEMPLATES_MAP:
            raise Exception(f"Unknown request template id: {template_id}")

        request = TEMPLATES_MAP[template_id]()
        for k, v in kwargs.items():
            self._set_pb_field(request, k, v)

        self.logger.debug(f"Sending message {MessageToDict(request)}")

        buffer = self._convert_request_to_bytes(request)
        await self._send(buffer)

        return template_id

    async def _send_and_recv(self, **kwargs):
        """
        Sends a request to the API and decode the response
        """

        async with self.lock:
            template_id = await self._send_request(**kwargs)

        while True:
            async with DisconnectionHandler(self):
                async with self.lock:
                    buffer = await self._recv()

                response = self._convert_bytes_to_response(buffer)
                self.logger.debug(f"Received message {MessageToDict(response)}")

                if not hasattr(response, "rp_code") or response.template_id != template_id + 1:
                    await self._process_response(response)
                    continue

                break

        if len(response.rp_code) and response.rp_code[0] != '0':
            raise RithmicErrorResponse(f"Rithmic returned an error={MessageToDict(response)} for the request={kwargs}")

        return response

    async def _send_and_collect(self, template_id, **kwargs):
        """
        Send a request, wait for the RequestManager to collect related responses asynchronously
        And return the array of responses
        """

        if "account_id" in kwargs and kwargs["account_id"] is None:
            # Request does not need an account id
            kwargs.pop("account_id")
        else:
            account_id = self.client.plants["order"]._get_account_id(**kwargs)
            kwargs["account_id"] = account_id

            login_info = self.client.plants["order"].login_info
            kwargs["fcm_id"] = login_info["fcm_id"]
            kwargs["ib_id"] = login_info["ib_id"]

        request_id = self._generate_request_id()

        return await self.request_manager.send_and_collect(
            user_msg=request_id,
            template_id=template_id,
            **kwargs
        )

    def _generate_request_id(self):
        return str(uuid.uuid4())

    def _convert_request_to_bytes(self, request):
        """
        Request class to bytes conversion
        """
        serialized = request.SerializeToString()
        length = len(serialized)
        buffer = length.to_bytes(4, byteorder='big', signed=True)
        buffer += serialized
        return buffer

    def _convert_bytes_to_response(self, buffer):
        """
        Bytes to Response class conversion
        """
        raw_data = buffer[4:]

        # Parse as base to extract template_id
        base = pb.base_pb2.Base()
        base.ParseFromString(raw_data)

        template_id = base.template_id
        if template_id not in TEMPLATES_MAP:
            raise Exception(f"Unknown template ID: {template_id}")

        # Parse as specific response class
        response_cls = TEMPLATES_MAP[template_id]
        response = response_cls()
        response.ParseFromString(raw_data)

        return response

    def _set_pb_field(self, obj, field_name, value):
        field_descriptor = obj.DESCRIPTOR.fields_by_name[field_name]

        if field_descriptor.label == FieldDescriptor.LABEL_REPEATED:
            # Handle repeated fields (lists in protobuf)
            field = getattr(obj, field_name)
            if isinstance(value, list):
                field.extend(value)
            else:
                field.append(value)
        elif field_descriptor.type == FieldDescriptor.TYPE_MESSAGE:
            # Handle nested message fields
            nested_message = getattr(obj, field_name)
            for sub_key, sub_value in value.items():
                self._set_pb_field(nested_message, sub_key, sub_value)
        else:
            # Handle normal fields
            try:
                setattr(obj, field_name, value)
            except:
                self.logger.error(f"Error when trying to set {field_name}")
                raise

    async def _send_heartbeat(self):
        async with self.lock:
            await self._send_request(template_id=18)

    async def _listen(self):
        while True:
            try:
                async with DisconnectionHandler(self):
                    async with self.lock:
                        buffer = await asyncio.wait_for(self._recv(), timeout=self.listen_interval)

                    response = self._convert_bytes_to_response(buffer)
                    self.logger.debug(f"Received message {MessageToDict(response)}")

                    await self._process_response(response)

            except asyncio.TimeoutError:
                pass

            except asyncio.CancelledError:
                break

            except:
                self.logger.exception("Exception in background listener")

            if not self.last_message_time or not self.heartbeat_interval:
                continue

            # Send regular heartbeats
            if time.time() - self.last_message_time > self.heartbeat_interval - 2:
                await self._send_heartbeat()

    def _response_to_dict(self, response):
        data = MessageToDict(response, preserving_proto_field_name=True, use_integers_for_enums=True)

        data.pop("template_id", None)
        data.pop("request_key", None)
        data.pop("user_msg", None)
        data.pop("rq_handler_rp_code", None)
        data.pop("rp_code", None)

        return data

    async def _process_response(self, response):
        """
        Handles async responses
        """

        if response.template_id in [13, 19, 401]:
            # Ignore
            # - logout responses
            # - heartbeat responses
            # - pnl subscription responses
            return True

        if hasattr(response, "user_msg") and response.user_msg is not None and len(response.user_msg) > 0:
            request_id = response.user_msg[0]

            if self.request_manager.has_pending(request_id):
                if response.rp_code:
                    if response.rp_code[0] != '0':
                        request = self.request_manager.requests.get(request_id)
                        self.request_manager.mark_complete(request_id)
                        raise RithmicErrorResponse(f"Rithmic returned an error={MessageToDict(response)} for the request={request}")

                    else:
                        if response.template_id in [11, 15, 114, 301]:
                            # We expect a single response containing `rp_code` for these endpoints
                            self.request_manager.handle_response(response)

                        # Else: multiple response + a sentinel message with `rp_code`
                        self.request_manager.mark_complete(request_id)
                else:
                    self.request_manager.handle_response(response)

                return True

        return self.request_manager.handle_response(response)

    def _datetime_to_utc(self, dt: datetime):
        if dt.tzinfo is None:
            # Use system timezone
            system_timezone = pytz.timezone(str(get_localzone()))
            dt = system_timezone.localize(dt)

        if dt.tzinfo != pytz.utc:
            # Convert to utc
            dt = dt.astimezone(pytz.utc)

        return dt

    def _ssboe_usecs_to_datetime(self, ssboe: int, usecs: int):
        ts = '{0}.{1}'.format(ssboe, usecs)
        return datetime.fromtimestamp(float(ts), tz=pytz.utc)

    def _datetime_to_ssboe_usecs(self, dt: datetime):
        """
        Split the timestamp into integer seconds (ssboe) and rounded microseconds (usecs)
        """
        timestamp = dt.timestamp()

        ssboe = int(timestamp)
        usecs = round((timestamp - ssboe) * 1_000_000)

        return ssboe, usecs

    def _first(self, array):
        if not array:
            return None
        return array[0]
