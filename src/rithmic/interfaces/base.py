import inspect
from abc import ABCMeta
import asyncio
from asyncio import AbstractEventLoop
from datetime import datetime as dt
from pathlib import Path
from typing import Union, Callable

import pytz
import ssl
import threading
import websockets

from rithmic.callbacks.callbacks import CallbackManager
from rithmic.config.credentials import RithmicEnvironment, get_rithmic_credentials
from rithmic.protocol_buffers import base_pb2, request_login_pb2, response_login_pb2, request_heartbeat_pb2, \
    request_logout_pb2, request_reference_data_pb2, request_rithmic_system_info_pb2, response_rithmic_system_info_pb2
from rithmic.protocol_buffers.response_reference_data_pb2 import ResponseReferenceData
from rithmic.tools.pyrithmic_logger import logger


INFRA_MAP = {
    1: 'TICKER', 2: 'ORDER', 3: 'HISTORY'
}

SHARED_RESPONSE_MAP = {
    15: dict(proto=ResponseReferenceData, fn='process_reference_data_response')
}

def _setup_ssl_context():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    path = Path(__file__).parent.parent / 'certificates'
    localhost_pem = path / 'rithmic_ssl_cert_auth_params'
    ssl_context.load_verify_locations(localhost_pem)
    return ssl_context


class RithmicBaseApi(metaclass=ABCMeta):
    infra_type = None
    api_type = None

    def __init__(self, env: RithmicEnvironment = None, callback_manager: CallbackManager = None,
                 auto_connect: bool = True, loop: AbstractEventLoop = None):
        self.ws = None
        credentials = get_rithmic_credentials(env)
        self.env = env
        self.uri = credentials['uri']
        self.user = credentials['user']
        self.pw = credentials['pw']
        self.app_name = credentials['app_name']
        self.app_version = credentials['app_version']
        self.system_name = credentials['system_name']
        self.ssl_context = self.setup_ssl_context()
        self.callback_manager = None
        self.add_callback_manager(callback_manager)
        self.loop = None
        self.sent_messages = []
        self.recv_messages = []
        if loop is not None:
            self.loop = loop
        else:
            self.start_loop()
        if auto_connect:
            self.connect_and_login()
        self.reference_data_map = dict()

    async def _request_reference_data(self, security_code: str, exchange_code: str) -> Union[str, None]:
        """
        Create request for front month contract of a given underlying/exchange combination

        :param security_code: (str) valid security code
        :param exchange_code: (str) valid exchange code
        :return: (dict) the reference data
        """
        rq = request_reference_data_pb2.RequestReferenceData()

        key = (security_code, exchange_code)

        rq.template_id = 14
        rq.symbol = security_code
        rq.exchange = exchange_code
        rq.user_msg.append('{0}|{1}'.format(security_code, exchange_code))
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)
        while key not in self.reference_data_map:
            await asyncio.sleep(0.01)
        return self.reference_data_map[key]

    def process_reference_data_response(self, template_id: int, msg: ResponseReferenceData):
        if msg.rp_code[0] == '0':  # Good response
            result = dict(
                symbol_name=msg.symbol_name, expiry_date=dt.strptime(msg.expiration_date, '%Y%m%d').date(),
                underlying_code=msg.product_code, security_code=msg.symbol, exchange_code=msg.exchange,
                instrument_type=msg.instrument_type, currency=msg.currency,
                multiplier=msg.single_point_value, tick_multiplier=msg.min_qprice_change,
                tick_value = msg.single_point_value * msg.min_qprice_change,
            )
            self.reference_data_map[(msg.symbol, msg.exchange)] = result
        else:
            requested_key = tuple(msg.user_msg[0].split('|'))
            self.reference_data_map[requested_key] = None

    def add_callback_manager(self, callback_manager: Union[CallbackManager, None]):
        self.callback_manager = callback_manager if callback_manager is not None else CallbackManager()

    def detach_callback_manager(self):
        self.callback_manager = CallbackManager()

    @property
    def is_connected(self) -> bool:
        return self.ws.open

    async def send_buffer(self, message: bytes):
        self.sent_messages.append(message)
        await self.ws.send(message)

    async def recv_buffer(self):
        message = await self.ws.recv()
        self.recv_messages.append(message)
        return message

    async def _consume_subscription(self):
        raise NotImplementedError('Must be implemented in non abstract class')

    def start_loop(self):
        self.loop = asyncio.new_event_loop()
        self.thr = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thr.start()

    def get_template_id_from_message_buffer(self, msg_buf) -> int:
        msg_length = int.from_bytes(msg_buf[0:3], byteorder='big', signed=True)
        base = base_pb2.Base()
        base.ParseFromString(msg_buf[4:])
        return base.template_id

    def _convert_request_to_bytes(self, request):
        serialized = request.SerializeToString()
        length = len(serialized)
        buffer = bytearray()
        buffer = length.to_bytes(4, byteorder='big', signed=True)
        buffer += serialized
        return buffer

    def setup_ssl_context(self):
        return _setup_ssl_context()

    def connect_and_login(self):
        """
        Clients should follow the below sequence for communicating with protocol server,
        1. Open a websocket, upon connecting send 'RequestRithmicSystemInfo' message.
           Parse the response and record list of 'system names' available. Close this connection

        2. Open a new websocket, and login using the desired 'system_name'.
        """
        ws = self._get_websocket_connection()
        self.ws = ws

        future = asyncio.run_coroutine_threadsafe(self.get_system_names(), loop=self.loop)
        system_names = future.result()
        print("ZZZZ", system_names)

        future = asyncio.run_coroutine_threadsafe(self.disconnect_from_rithmic(), loop=self.loop)
        future.result()

        if self.system_name not in system_names:
            raise Exception(f"You must specify valid SYSTEM_NAME in the credentials file: {system_names}")

        ws = self._get_websocket_connection()
        self.ws = ws
        log_in_details = self._log_into_rithmic()
        logger.info('Connected to {0} as User {1} on {2} ({3})'.format(
            self.api_type, self.user, self.system_name, self.env
        ))
        print("AAAA", log_in_details)
        return log_in_details

    def _get_websocket_connection(self):
        future = asyncio.run_coroutine_threadsafe(self.get_websocket_connection(), self.loop)
        return future.result()

    def _log_into_rithmic(self):
        future = asyncio.run_coroutine_threadsafe(self.rithmic_login(), loop=self.loop)
        return future.result()

    async def get_websocket_connection(self):
        ws = await websockets.connect(self.uri, ssl=self.ssl_context, ping_interval=3)
        logger.info('Connected to {0}'.format(self.uri))
        return ws

    async def get_system_names(self):
        rq = request_rithmic_system_info_pb2.RequestRithmicSystemInfo()
        rq.template_id = 16
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

        rp_buf = await self.recv_buffer()
        rp = response_rithmic_system_info_pb2.ResponseRithmicSystemInfo()
        rp.ParseFromString(rp_buf[4:])

        return rp.system_name

    async def rithmic_login(self):
        rq = request_login_pb2.RequestLogin()
        rq.template_id = 10
        rq.template_version = "3.9"
        rq.user = self.user
        rq.password = self.pw
        rq.app_name = self.app_name
        rq.app_version = self.app_version
        rq.system_name = self.system_name
        rq.infra_type = self.infra_type
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

        rp_buf = await self.recv_buffer()
        rp = response_login_pb2.ResponseLogin()
        rp.ParseFromString(rp_buf[4:])

        if rp.rp_code[0] != '0':
            raise ConnectionError(f"Login failed: {', '.join(rp.rp_code)}")

        logger.info('Logged into Rithmic => unique user id={0}; Plant=>{1}'.format(
            rp.unique_user_id, INFRA_MAP[self.infra_type])
        )
        return rp

    async def send_heartbeat(self):
        rq = request_heartbeat_pb2.RequestHeartbeat()
        rq.template_id = 18
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)
        logger.debug('Sent Heartbeat Request')

    def _get_row_information(self, template_id, msg):
        ts = '{0}.{1}'.format(msg.ssboe, msg.usecs)
        update_time = dt.fromtimestamp(float(ts), tz=pytz.utc)
        msg = self._convert_msg_to_dict(msg)
        row = dict(template_id=template_id, update_time=update_time)
        row.update(msg)
        return row

    def _convert_msg_to_dict(self, msg):
        result = dict()
        keys = [x.split(':')[0] for x in str(msg).strip().split('\n')]
        for k in keys:
            result[k] = getattr(msg, k)
        return result

    async def rithmic_logout(self):
        rq = request_logout_pb2.RequestLogout()
        rq.template_id = 12
        rq.user_msg.append("logging out")
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    async def disconnect_from_rithmic(self):
        await self.ws.close(1000, "Closing Connection")

    def disconnect_and_logout(self):
        if self.ws.open:
            logger.info('Logging Out of Rithmic')
            future = asyncio.run_coroutine_threadsafe(self.rithmic_logout(), loop=self.loop)
            logout = future.result()
            logger.info('Disconnected')
            future = asyncio.run_coroutine_threadsafe(self.disconnect_from_rithmic(), loop=self.loop)
            disconnect = future.result()
            logger.info('Logged out and Disconnected')
        else:
            logger.info('Connection already closed, exiting...')

    def perform_callback(self, func: Callable, args: list):
        if inspect.iscoroutinefunction(func):
            asyncio.run_coroutine_threadsafe(func(*args), loop=self.loop)
        else:
            func(*args)

    def get_reference_data(self, security_code: str, exchange_code: str) -> Union[dict, None]:
        """
        Get the current Front Month Contract of an underlying code and exchange, eg ES and CME
        :param security_code: (str) valid security code
        :param exchange_code: (str) valid exchange code
        :return: (dict) reference data
        """
        key = (security_code, exchange_code)
        if key in self.reference_data_map:
            return self.reference_data_map[key]
        ref_data = asyncio.run_coroutine_threadsafe(
            self._request_reference_data(security_code, exchange_code), loop=self.loop
        ).result()
        return ref_data
