import asyncio
import logging
import pickle
import time
from datetime import datetime as dt
from pathlib import Path
from typing import Union

import pandas as pd
from pandas import DataFrame

from rithmic.callbacks.callbacks import CallbackManager
from rithmic.config.credentials import RithmicEnvironment
from rithmic.interfaces.base import RithmicBaseApi, SHARED_RESPONSE_MAP
from rithmic.interfaces.order.status_manager import StatusManager
from rithmic.interfaces.order.order_types import BracketOrder, VALID_ORDER_TYPES, MarketOrder, LimitOrder
from rithmic.protocol_buffers import (
    request_login_pb2, request_login_info_pb2, response_login_info_pb2, request_account_list_pb2,
    response_account_list_pb2, request_trade_routes_pb2, response_trade_routes_pb2,
    request_subscribe_for_order_updates_pb2, request_subscribe_to_bracket_updates_pb2, rithmic_order_notification_pb2,
    exchange_order_notification_pb2, response_bracket_order_pb2, response_new_order_pb2, request_new_order_pb2,
    request_bracket_order_pb2, request_cancel_order_pb2, request_update_stop_bracket_level_pb2,
    request_modify_order_pb2, request_update_target_bracket_level_pb2,
    request_account_rms_info_pb2, response_account_rms_info_pb2,
)
from rithmic.tools.general import dict_destructure, get_utc_now
from rithmic.tools.meta import ApiType
from rithmic.tools.pyrithmic_exceptions import (
    NoValidTradingAccountException, NoValidTradeRouteException, NoTradingConfigException, WebsocketClosedException,
)
from rithmic.tools.pyrithmic_logger import logger, configure_logging

ORDER_UPDATE_RESPONSE_MAP = {
    351: dict(proto=rithmic_order_notification_pb2.RithmicOrderNotification, fn='_process_rithmic_order_notification'),
    352: dict(proto=exchange_order_notification_pb2.ExchangeOrderNotification,
              fn='_process_exchange_order_notification'),
    331: dict(proto=response_bracket_order_pb2.ResponseBracketOrder, fn='_process_response_bracket_order'),
    313: dict(proto=response_new_order_pb2.ResponseNewOrder, fn='_process_response_new_order'),
}
ORDER_UPDATE_RESPONSE_MAP.update(SHARED_RESPONSE_MAP)

SIDE_MAP = {
    True: request_new_order_pb2.RequestNewOrder.TransactionType.BUY,
    False: request_new_order_pb2.RequestNewOrder.TransactionType.SELL,
}

BRACKET_SIDE_MAP = {
    True: request_bracket_order_pb2.RequestBracketOrder.TransactionType.BUY,
    False: request_bracket_order_pb2.RequestBracketOrder.TransactionType.SELL,
}


class RithmicOrderApi(RithmicBaseApi):
    """
    Rithmic Order API For the ORDER PLANT to submit orders, cancel orders, modify orders and receive fills
    """
    infra_type = request_login_pb2.RequestLogin.SysInfraType.ORDER_PLANT
    api_type = ApiType.ORDER

    USER_TYPE_MAP = {0: 'ADMIN', 1: 'FCM', 2: 'IB', 3: 'TRADER'}

    def __init__(self, env: RithmicEnvironment = None, callback_manager: CallbackManager = None, loop=None,
                 auto_connect: bool = True, recovered_status_manager: StatusManager = None):
        """
        Rithmic Order API init method

        :param env: (RithmicEnvironment) provide a rithmic environment to connect to, if omitted, tries to get the
                    default environment from the Environment Variable RITHMIC_ENVIRONMENT_NAME
        :param auto_connect: (bool) automatically connect and log into Rithmic, defaults to True
        :param callback_manager: (CallbackManager) provide a configured manager with callbacks registered
        :param loop: (AbstractEventLoop) asyncio event loop can be provided to share/use existing loop
        """
        self.status_manager: Union[StatusManager, None] = None
        self.add_status_manager(callback_manager, recovered_status_manager)
        self.have_trading_config = False
        self.subscribed_for_updates = False
        self._consuming_updates = False
        self.fcm_id = None
        self.ib_id = None
        self.user_type = None
        self.accounts = None
        self.trade_routes = None
        RithmicBaseApi.__init__(self, env=env, callback_manager=callback_manager, loop=loop, auto_connect=auto_connect)
        self.rithmic_updates_data = []
        self.exchange_updates_data = []

    def add_status_manager(self, callback_manager: CallbackManager = None,
                           recovered_status_manager: StatusManager = None):
        if recovered_status_manager is None:
            self.status_manager = StatusManager(callback_manager)
        else:
            recovered_status_manager.add_callback_manager(callback_manager)
            self.status_manager = recovered_status_manager

    def _set_log_in_details(self, details: dict) -> None:
        """
        Records log in details for further use

        :param details: (dict) data back from logging in
        :return: None
        """
        keys = ['fcm_id', 'ib_id', 'user_type', 'accounts', 'trade_routes']
        fcm_id, ib_id, user_type, accounts, trade_routes = dict_destructure(details, keys)
        self.fcm_id = fcm_id
        self.ib_id = ib_id
        self.user_type = user_type
        self.accounts = pd.DataFrame(accounts)
        self.trade_routes = pd.DataFrame(trade_routes)
        self.have_trading_config = True

    def connect_and_login(self) -> None:
        """Connects, Logs in to Rithmic and subscribes to updates"""
        super(RithmicOrderApi, self).connect_and_login()
        future = asyncio.run_coroutine_threadsafe(self._get_login_info(), loop=self.loop)
        log_in_details = future.result()
        logger.info('Order API Extended Login Details => {0}'.format(log_in_details))
        self._set_log_in_details(log_in_details)
        self.get_account_rms()
        self._run_update_subscription()

    async def _get_login_info(self) -> dict:
        """
        Gets extended login details for order management, accounts, trade routes etc
        :return: (dict) of account data
        """
        rq = request_login_info_pb2.RequestLoginInfo()
        rq.template_id = 300
        rq.user_msg.append("request_login_info")
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

        rp_buf = bytearray()
        rp_buf = await self.recv_buffer()

        rp_length = int.from_bytes(rp_buf[0:3], byteorder='big', signed=True)

        rp = response_login_info_pb2.ResponseLoginInfo()
        rp.ParseFromString(rp_buf[4:])

        if rp.rp_code[0] == '0':
            accounts = await self._list_accounts(rp.fcm_id, rp.ib_id, rp.user_type)
            trade_routes = await self._list_trade_routes()
            details = dict(
                template_id=rp.template_id, user_msg=rp.user_msg, rp_code=rp.rp_code,
                fcm_id=rp.fcm_id, ib_id=rp.ib_id, user_type=rp.user_type,
                user_type_string=self.USER_TYPE_MAP[rp.user_type],
                accounts=accounts, trade_routes=trade_routes,
            )
            return details
        raise ConnectionError(f"Error Getting Details from Rithmic: {', '.join(rp.rp_code)}")

    async def _list_accounts(self, fcm_id: str, ib_id: str, user_type: int) -> list:
        """
        Retrieves account information valid for the user

        :param fcm_id: (str) FCM id to use
        :param ib_id: (str) Broker id to use
        :param user_type: (int) User type per rithmic mapping as an integer
        :return: (list) list of accounts configured for user
        """
        rq = request_account_list_pb2.RequestAccountList()
        rq.template_id = 302
        rq.user_msg.append("hello")
        rq.fcm_id = fcm_id
        rq.ib_id = ib_id
        rq.user_type = user_type

        buffer = self._convert_request_to_bytes(rq)
        rp_is_done = False
        await self.send_buffer(buffer)

        rp_buf = bytearray()

        accounts = []
        while rp_is_done == False:
            rp_buf = await self.recv_buffer()
            # get length from first four bytes from rp_buf
            rp_length = int.from_bytes(rp_buf[0:3], byteorder='big', signed=True)
            rp = response_account_list_pb2.ResponseAccountList()
            rp.ParseFromString(rp_buf[4:])

            record = dict(
                template_id=rp.template_id, rq_handler_rp_code=rp.rq_handler_rp_code,
                rp_code=rp.rp_code, fcm_id=rp.fcm_id, ib_id=rp.ib_id, account_id=rp.account_id,
                account_name=rp.account_name,
            )
            if len(rp.rp_code) > 0:
                rp_is_done = True
            else:
                accounts.append(record)
        return accounts

    async def _list_trade_routes(self) -> list:
        """Returns list of trade routes configured for user"""
        rq = request_trade_routes_pb2.RequestTradeRoutes()
        rq.template_id = 310
        rq.user_msg.append("request_trade_routes")
        rq.subscribe_for_updates = False

        buffer = self._convert_request_to_bytes(rq)
        rp_is_done = False
        await self.send_buffer(buffer)

        rp_buf = bytearray()
        trade_routes = []
        while rp_is_done == False:
            rp_buf = await self.recv_buffer()
            rp_length = int.from_bytes(rp_buf[0:3], byteorder='big', signed=True)
            rp = response_trade_routes_pb2.ResponseTradeRoutes()
            rp.ParseFromString(rp_buf[4:])
            record = dict(
                template_id=rp.template_id, rp_handler_code=rp.rq_handler_rp_code, rp_code=rp.rp_code,
                fcm_id=rp.fcm_id, ib_id=rp.ib_id, exchange=rp.exchange, trade_route=rp.trade_route,
                status=rp.status, is_default=rp.is_default,
            )
            if len(rp.rp_code) > 0:
                rp_is_done = True
            else:
                trade_routes.append(record)
        return trade_routes

    @property
    def primary_account_id(self) -> str:
        """Gets the primary account to use for trading"""
        if len(self.accounts) == 0:
            raise NoValidTradingAccountException('No Valid Trading Accounts Found')
        return self.accounts.iloc[0].account_id

    def _get_trade_route(self, exchange_code: str) -> str:
        """Gets the correct trade route for an exchange"""
        df = self.trade_routes
        df = df[df.exchange == exchange_code]
        if len(df) == 0:
            raise NoValidTradeRouteException('No Valid Trade Route Exists for {0}'.format(exchange_code))
        return df.iloc[0].trade_route

    async def _subscribe_for_order_updates(self, fcm_id, ib_id, account_id) -> None:
        """Creates and sends a request for order updates subscription"""
        rq = request_subscribe_for_order_updates_pb2.RequestSubscribeForOrderUpdates()
        rq.template_id = 308
        rq.user_msg.append("order_updates_subscription")
        rq.fcm_id = fcm_id
        rq.ib_id = ib_id
        rq.account_id = account_id
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    async def _subscribe_for_bracket_updates(self, fcm_id, ib_id, account_id):
        """Creates and sends a request for bracket updates subscription"""
        rq = request_subscribe_to_bracket_updates_pb2.RequestSubscribeToBracketUpdates()
        rq.template_id = 336
        rq.user_msg.append('bracket_updates_subscription')
        rq.fcm_id = fcm_id
        rq.ib_id = ib_id
        rq.account_id = account_id
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    def _check_update_status(self):
        """Confirm everything is configured and subscription consumption requests sent"""
        if self.have_trading_config:
            if self.subscribed_for_updates is False:
                primary_account = self.primary_account_id
                asyncio.run_coroutine_threadsafe(
                    self._subscribe_for_order_updates(self.fcm_id, self.ib_id, primary_account), loop=self.loop
                )
                asyncio.run_coroutine_threadsafe(
                    self._subscribe_for_bracket_updates(self.fcm_id, self.ib_id, primary_account), loop=self.loop,
                )
                self.subscribed_for_updates = True
        else:
            raise NoTradingConfigException('Have not received Trading Config from Rithmic')

    async def _consume_order_updates(self):
        """
        Consumes new messages as data is streamed, sends a heartbeat if no data received after 5 seconds and
        the websocket is still open. Starts once api is connected and logged in.

        :return: None
        """
        self._consuming_updates = True
        await self.send_heartbeat()
        connected = True
        while connected:
            try:
                msg_buf = bytearray()
                waiting_for_msg = True
                while waiting_for_msg:
                    try:
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
                elif template_id == 13:
                    connected = False
                    continue
                else:
                    result = self._process_order_update(template_id, msg_buf)
            except Exception as e:
                print(e)

    def _process_order_update(self, template_id: int, msg_buf) -> Union[dict, None]:
        """
        Process and route update message to the correct processing method

        :param template_id: (int) template id of the message
        :param msg_buf: (bytes) message from rithmic
        :return: (dict or None) data processed
        """
        if template_id in ORDER_UPDATE_RESPONSE_MAP:
            meta = ORDER_UPDATE_RESPONSE_MAP[template_id]
            msg = meta['proto']()
            msg.ParseFromString(msg_buf[4:])
            fn = getattr(self, meta['fn'])
            result = fn(template_id, msg)
            callback_fn = self.callback_manager.get_callback_by_template_id(template_id)
            if callback_fn is not None:
                self.perform_callback(callback_fn, [result])
            return result
        else:
            x = 1

    def _process_response_bracket_order(self, template_id, msg) -> dict:
        """Handles a bracket order response message"""
        row = self._get_row_information(template_id, msg)
        order_id = row.get('user_tag')
        basket_id = row.get('basket_id')
        return row

    def _process_rithmic_order_notification(self, template_id, msg) -> dict:
        """Handles a rithmic update response message"""
        row = self._get_row_information(template_id, msg)
        row['order_id'] = row.get('user_tag')
        self.rithmic_updates_data.append(row)
        self.status_manager._process_rithmic_update(row)
        return row

    def _process_exchange_order_notification(self, template_id, msg) -> dict:
        """Handles an exchange update response message"""
        row = self._get_row_information(template_id, msg)
        row['order_id'] = row.get('user_tag')
        self.exchange_updates_data.append(row)
        self.status_manager._process_exchange_update(row)
        return row

    def _process_response_new_order(self, template_id, msg) -> dict:
        """Handles a new order response message"""
        row = self._get_row_information(template_id, msg)
        order_id = row.get('user_tag')
        basket_id = row.get('basket_id')
        return row

    def _run_update_subscription(self) -> None:
        """Check config and start consumption process"""
        self._check_update_status()
        if self._consuming_updates is False:
            asyncio.run_coroutine_threadsafe(self._consume_order_updates(), self.loop)

    @property
    def rithmic_updates(self) -> DataFrame:
        """Returns rithmic update messages in a pandas dataframe"""
        data = self.rithmic_updates_data[:]
        return pd.DataFrame(data)

    @property
    def exchange_updates(self) -> DataFrame:
        """Returns exchange update messages in a pandas dataframe"""
        data = self.exchange_updates_data[:]
        return pd.DataFrame(data)

    async def _send_market_order(self, order_id: str, security_code: str, exchange_code: str, quantity: int,
                                 is_buy: bool) -> None:
        """
        Creates and sends a request to submit a market order to the exchange

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :return: None
        """
        rq = request_new_order_pb2.RequestNewOrder()
        rq.template_id = 312
        rq.user_tag = order_id
        rq.fcm_id = self.fcm_id
        rq.ib_id = self.ib_id
        rq.account_id = self.primary_account_id
        rq.exchange = exchange_code
        rq.symbol = security_code
        rq.quantity = quantity
        rq.transaction_type = SIDE_MAP[is_buy]
        rq.duration = request_new_order_pb2.RequestNewOrder.Duration.DAY
        rq.price_type = request_new_order_pb2.RequestNewOrder.PriceType.MARKET
        rq.manual_or_auto = request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL
        rq.trade_route = self._get_trade_route(exchange_code)
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    async def _send_limit_order(self, order_id: str, security_code: str, exchange_code: str, quantity: int,
                                is_buy: bool,
                                limit_price: float) -> None:
        """
        Creates and sends a request to submit a limit order to the exchange

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :param limit_price: (float) Upper/Lower limit for a Buy/Sell to fill at
        :return: None
        """
        rq = request_new_order_pb2.RequestNewOrder()
        rq.template_id = 312
        rq.user_tag = order_id
        rq.fcm_id = self.fcm_id
        rq.ib_id = self.ib_id
        rq.account_id = self.primary_account_id
        rq.exchange = exchange_code
        rq.symbol = security_code
        rq.quantity = quantity
        rq.transaction_type = SIDE_MAP[is_buy]
        rq.duration = request_new_order_pb2.RequestNewOrder.Duration.DAY
        rq.price_type = request_new_order_pb2.RequestNewOrder.PriceType.LIMIT
        rq.manual_or_auto = request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL
        rq.trade_route = self._get_trade_route(exchange_code)
        rq.price = limit_price
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    async def _send_bracket_order(self, order_id: str, security_code: str, exchange_code: str, quantity: int,
                                  is_buy: bool, limit_price: float, take_profit_ticks: int,
                                  stop_loss_ticks: int) -> None:
        """
        Creates and sends a request to submit a bracket order to the exchange

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :param limit_price: (float) Upper/Lower limit for a Buy/Sell to fill the parent at
        :param take_profit_ticks: (int) Number of ticks from limit price to set Take Profit Limit Price
        :param stop_loss_ticks: (int) Number of ticks from limit price to set Stop Loss Trigger Price
        :return: None
        """
        rq = request_bracket_order_pb2.RequestBracketOrder()
        rq.template_id = 330
        rq.user_tag = order_id
        rq.fcm_id = self.fcm_id
        rq.ib_id = self.ib_id
        rq.account_id = self.primary_account_id
        rq.exchange = exchange_code
        rq.symbol = security_code
        rq.quantity = quantity
        rq.transaction_type = BRACKET_SIDE_MAP[is_buy]
        rq.duration = request_bracket_order_pb2.RequestBracketOrder.Duration.DAY
        rq.bracket_type = request_bracket_order_pb2.RequestBracketOrder.BracketType.TARGET_AND_STOP_STATIC
        rq.price_type = request_bracket_order_pb2.RequestBracketOrder.PriceType.LIMIT
        rq.price = limit_price
        rq.trade_route = self._get_trade_route(exchange_code)
        rq.manual_or_auto = request_bracket_order_pb2.RequestBracketOrder.OrderPlacement.MANUAL
        rq.target_quantity = quantity
        rq.target_ticks = take_profit_ticks
        rq.stop_quantity = quantity
        rq.stop_ticks = stop_loss_ticks
        rq.user_type = request_bracket_order_pb2.RequestBracketOrder.UserType.USER_TYPE_TRADER
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    def submit_market_order(self, order_id: str, security_code: str, exchange_code: str, quantity: int,
                            is_buy: bool) -> MarketOrder:
        """
        Submit a Market Order to the Broker

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :return: (MarketOrder) market order
        """
        market_order = self.status_manager._add_market_order(order_id, security_code, exchange_code, quantity, is_buy)
        asyncio.run_coroutine_threadsafe(
            self._send_market_order(order_id, security_code, exchange_code, quantity, is_buy), loop=self.loop
        )
        return market_order

    def submit_bracket_order(self, order_id: str, security_code: str, exchange_code: str, quantity: int, is_buy: bool,
                             limit_price: float, take_profit_ticks: int, stop_loss_ticks: int, ) -> BracketOrder:
        """
        Submit a Bracket Order to the Broker

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :param limit_price: (float) Upper/Lower limit for a Buy/Sell to fill the parent at
        :param take_profit_ticks: (int) Number of ticks from limit price to set Take Profit Limit Price
        :param stop_loss_ticks: (int) Number of ticks from limit price to set Stop Loss Trigger Price
        :return: (BracketOrder) bracket order
        """
        ref_data = self.get_reference_data(security_code, exchange_code)
        bracket_order = self.status_manager._add_bracket_order(
            order_id, security_code, exchange_code, quantity, is_buy, limit_price, take_profit_ticks, stop_loss_ticks,
            ref_data['tick_multiplier'],
        )
        asyncio.run_coroutine_threadsafe(self._send_bracket_order(
            order_id, security_code, exchange_code, quantity, is_buy, limit_price, take_profit_ticks, stop_loss_ticks
        ), loop=self.loop)
        return bracket_order

    def submit_limit_order(self, order_id: str, security_code: str, exchange_code: str, quantity: int,
                           is_buy: bool, limit_price: float) -> LimitOrder:
        """
        Submit a Limit Order to the Broker

        :param order_id: (str) Unique string per order
        :param security_code: (str) Valid Security Code
        :param exchange_code: (str) Valid Exchange Code
        :param quantity: (int) Quantity in lots of the Order
        :param is_buy: (bool) True for a Buy, False for a Sell
        :param limit_price: (float) Upper/Lower limit for a Buy/Sell to fill the order at
        :return: (LimitOrder) limit order
        """
        limit_order = self.status_manager._add_limit_order(
            order_id, security_code, exchange_code, quantity, is_buy, limit_price
        )
        asyncio.run_coroutine_threadsafe(self._send_limit_order(
            order_id, security_code, exchange_code, quantity, is_buy, limit_price,
        ), loop=self.loop)
        return limit_order

    async def _send_cancel_order(self, basket_id: str) -> None:
        """Create and send request to cancel existing order"""
        rq = request_cancel_order_pb2.RequestCancelOrder()
        rq.template_id = 316
        rq.user_msg.append('cancel_order')
        rq.fcm_id = self.fcm_id
        rq.ib_id = self.ib_id
        rq.account_id = self.primary_account_id
        rq.basket_id = basket_id
        rq.manual_or_auto = request_cancel_order_pb2.RequestCancelOrder.OrderPlacement.MANUAL
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    def _add_account_info_to_request(self, rq):
        rq.fcm_id = self.fcm_id
        rq.ib_id = self.ib_id
        rq.account_id = self.primary_account_id
        return rq

    def submit_cancel_order(self, order_id: str) -> None:
        """
        Submit an order cancellation to the broker

        :param order_id: (str) valid order id
        :return: None
        """
        order = self.get_order_by_order_id(order_id)
        asyncio.run_coroutine_threadsafe(self._send_cancel_order(order.basket_id), loop=self.loop)

    def submit_cancel_bracket_order_all_children(self, order_id: str) -> None:
        """
        Submit cancellations for all children of a bracket order

        :param order_id: (str) order id of the parent order
        :return:
        """
        parent_order = self.get_order_by_order_id(order_id)
        for order in parent_order.stop_loss_orders:
            asyncio.run_coroutine_threadsafe(self._send_cancel_order(order.basket_id), loop=self.loop)

    async def _send_bracket_order_stop_amendment(self, basket_id: str, old_stop_ticks: int,
                                                 new_stop_ticks: int) -> None:
        """
        Create and send request to modify the stop ticks on a unfilled bracket order

        :param basket_id: (str) basket id of the bracket order
        :param old_stop_ticks: (int) previous stop ticks
        :param new_stop_ticks: (int) new stop ticks
        :return: None
        """
        rq = request_update_stop_bracket_level_pb2.RequestUpdateStopBracketLevel()
        rq.template_id = 334
        rq = self._add_account_info_to_request(rq)
        rq.basket_id = basket_id
        rq.level = old_stop_ticks
        rq.stop_ticks = new_stop_ticks
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    async def _send_stop_loss_order_amendment(self, basket_id: str, symbol: str, exchange: str, quantity: int,
                                              stop_loss: float) -> None:
        """
        Create and send a request to amend a stop loss order

        :param basket_id: (str) basket id of the stop
        :param symbol: (str) valid symbol
        :param exchange: (str) valid exchange
        :param quantity: (int) quantity to amend
        :param stop_loss: (float) new trigger price
        :return: None
        """
        rq = request_modify_order_pb2.RequestModifyOrder()
        rq.template_id = 314
        rq = self._add_account_info_to_request(rq)
        rq.basket_id = basket_id
        rq.symbol = symbol
        rq.exchange = exchange
        rq.quantity = quantity
        rq.trigger_price = stop_loss
        rq.price_type = request_modify_order_pb2.RequestModifyOrder.PriceType.STOP_MARKET
        rq.manual_or_auto = request_modify_order_pb2.RequestModifyOrder.OrderPlacement.MANUAL

        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    async def _send_limit_order_amendment(self, basket_id: str, symbol: str, exchange: str, quantity: int,
                                          limit_price: float) -> None:
        """
        Create and send a request to amend a take profit order

        :param basket_id: (str) basket id of the stop
        :param symbol: (str) valid symbol
        :param exchange: (str) valid exchange
        :param quantity: (int) quantity to amend
        :param limit_price: (float) new limit price
        :return: None
        """
        rq = request_modify_order_pb2.RequestModifyOrder()
        rq.template_id = 314
        rq = self._add_account_info_to_request(rq)
        rq.basket_id = basket_id
        rq.symbol = symbol
        rq.exchange = exchange
        rq.quantity = quantity
        rq.price = limit_price
        rq.price_type = request_modify_order_pb2.RequestModifyOrder.PriceType.LIMIT
        rq.manual_or_auto = request_modify_order_pb2.RequestModifyOrder.OrderPlacement.MANUAL

        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    async def _send_bracket_order_target_amendment(self, basket_id: str, old_target_ticks: int,
                                                   new_target_ticks: int) -> None:
        """
        Create and send request to amend target ticks of take profit on unfilled bracket order

        :param basket_id: (str) basket id of the parent
        :param old_target_ticks: (int) current ticks to take profit
        :param new_target_ticks: (int) new ticks to take profit
        :return: None
        """
        rq = request_update_target_bracket_level_pb2.RequestUpdateTargetBracketLevel()
        rq.template_id = 332
        rq = self._add_account_info_to_request(rq)
        rq.basket_id = basket_id
        rq.level = old_target_ticks
        rq.target_ticks = new_target_ticks
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

    def submit_amend_bracket_order_stop_size(self, order_id: str, old_stop_ticks: int, new_stop_ticks: int) -> None:
        """
        Submit to broker to change the stop ticks on an unfilled bracket order

        :param basket_id: (str) basket id of the bracket order
        :param old_stop_ticks: (int) previous stop ticks
        :param new_stop_ticks: (int) new stop ticks
        :return:
        """
        order = self.get_order_by_order_id(order_id)
        asyncio.run_coroutine_threadsafe(
            self._send_bracket_order_stop_amendment(order.basket_id, old_stop_ticks, new_stop_ticks), loop=self.loop,
        )

    def submit_amend_bracket_order_take_profit_size(self, basket_id: str, old_target_ticks: int,
                                                    new_target_ticks: int) -> None:
        """
          Submit to broker to amend target ticks of take profit on unfilled bracket order

        :param basket_id: (str) basket id of the parent
        :param old_target_ticks: (int) current ticks to take profit
        :param new_target_ticks: (int) new ticks to take profit
        :return: None
        """
        asyncio.run_coroutine_threadsafe(
            self._send_bracket_order_target_amendment(basket_id, old_target_ticks, new_target_ticks),
            loop=self.loop,
        )

    def submit_amend_stop_loss_order(self, order_id: str, security_code: str, exchange_code: str, quantity: int,
                                     stop_loss: float) -> None:
        """
        Submit to the Broker amendment of stop trigger price of stop in the market

        :param order_id: (str) order id of the stop loss child
        :param security_code: (str) order security code
        :param exchange_code: (str) order exchange code
        :param quantity: (int) quantity to amend
        :param stop_loss: (float) new trigger price
        :return: None
        """
        order = self.get_order_by_order_id(order_id)
        asyncio.run_coroutine_threadsafe(
            self._send_stop_loss_order_amendment(order.basket_id, security_code, exchange_code, quantity, stop_loss),
            loop=self.loop,
        )

    def submit_amend_limit_order(self, order_id: str, security_code: str, exchange_code: str, quantity: int,
                                 limit_price: float):
        """
        Submit to the Broker amendment of limit price of a Limit order or child take profit order

        :param order_id: (str) order id of the limit or take profit order
        :param security_code: (str) order security code
        :param exchange_code: (str) order exchange code
        :param quantity: (int) quantity to amend
        :param limit_price: (float) new limit price
        :return: None
        """
        order = self.get_order_by_order_id(order_id)
        asyncio.run_coroutine_threadsafe(
            self._send_limit_order_amendment(order.basket_id, security_code, exchange_code, quantity, limit_price),
            loop=self.loop,
        )

    def submit_amend_bracket_order_all_stop_loss_orders(self, order_id: str, stop_loss: float) -> None:
        """
        Submits amendments of stop loss of all child stops belonging to a parent bracket order

        :param order_id: (str) order id of the bracket order
        :param stop_loss: (float) new stop loss trigger price
        :return: None
        """
        parent_order = self.get_order_by_order_id(order_id)
        current_stop_loss = parent_order.stop_loss_trigger_price
        assert isinstance(parent_order, BracketOrder)
        next_modified_count = parent_order.all_stops_modified_count + 1
        modify_map = dict()
        for stop_order in parent_order.stop_loss_orders:
            modify_map[stop_order.order_id] = stop_order.modify_count + 1
            asyncio.run_coroutine_threadsafe(
                self._send_stop_loss_order_amendment(
                    stop_order.basket_id, stop_order.security_code, stop_order.exchange_code, stop_order.quantity,
                    stop_loss
                ),
                loop=self.loop,
            )
        complete = False
        while not complete:
            if all([stop.modify_count == modify_map[stop.order_id] for stop in parent_order.stop_loss_orders]):
                complete = True
                parent_order.all_stops_modified_count = next_modified_count
                parent_order.all_stops_modified = True
        parent_order.update_stop_loss_trigger_price(stop_loss)
        parent_order.all_stops_modified_history[next_modified_count] = dict(
            modified_at=get_utc_now(), new_stop_loss=stop_loss, old_stop_loss=current_stop_loss
        )

    def submit_amend_bracket_order_all_take_profit_orders(self, order_id: str, limit_price: float) -> None:
        """
        Submits amendments of limit price of all child take profits belonging to a parent bracket order

        :param order_id: (str) order id of the bracket order
        :param limit_price: (float) new limit price
        :return: None
        """
        parent_order = self.get_order_by_order_id(order_id)
        current_take_profit = parent_order.take_profit_limit_price
        assert isinstance(parent_order, BracketOrder)
        next_modified_count = parent_order.all_take_profit_modified_count + 1
        modify_map = dict()
        for take_profit_order in parent_order.take_profit_orders:
            modify_map[take_profit_order.order_id] = take_profit_order.modify_count + 1
            asyncio.run_coroutine_threadsafe(
                self._send_limit_order_amendment(
                    take_profit_order.basket_id, take_profit_order.security_code, take_profit_order.exchange_code,
                    take_profit_order.quantity, limit_price
                ),
                loop=self.loop,
            )
        complete = False
        while not complete:
            if all([tp.modify_count == modify_map[tp.order_id] for tp in parent_order.take_profit_orders]):
                complete = True
                parent_order.all_take_profit_modified_count = next_modified_count
                parent_order.all_take_profit_modified = True
        parent_order.update_take_profit_limit_price(limit_price)
        parent_order.all_take_profit_modified_history[next_modified_count] = dict(
            modified_at=get_utc_now(), new_take_profit=limit_price, old_take_profit=current_take_profit
        )

    def get_order_by_order_id(self, order_id: str) -> VALID_ORDER_TYPES:
        return self.status_manager._get_order_by_order_id(order_id)

    def add_callback_manager(self, callback_manager: Union[CallbackManager, None]):
        super(RithmicOrderApi, self).add_callback_manager(callback_manager)
        self.status_manager.add_callback_manager(callback_manager)

    def save_status_manager_state(self, file_path: Path):
        with open(file_path, 'wb') as fp:
            state = self.status_manager
            pickle.dump(state, fp)

    def get_account_rms(self):
        future = asyncio.run_coroutine_threadsafe(self._get_account_rms(), loop=self.loop)
        details = future.result()

    async def _get_account_rms(self):
        rq = request_account_rms_info_pb2.RequestAccountRmsInfo()
        rq.template_id = 304
        rq.user_msg.append("request_account_rms_info")
        rq.fcm_id = self.fcm_id
        rq.ib_id = self.ib_id
        rq.user_type = self.user_type
        buffer = self._convert_request_to_bytes(rq)
        await self.send_buffer(buffer)

        rp_buf = await self.recv_buffer()

        rp = response_account_rms_info_pb2.ResponseAccountRmsInfo()
        rp.ParseFromString(rp_buf[4:])

        print(rp)

        details = dict(
            template_id=rp.template_id, user_msg=rp.user_msg, rp_code=rp.rp_code,
            fcm_id=rp.fcm_id, ib_id=rp.ib_id, account_id=rp.account_id,
            current=rp.currency, status=rp.status, algorithm=rp.algorithm,

            min_account_balance=rp.min_account_balance,
            min_margin_balance=rp.min_margin_balance,
            check_min_account_balance=rp.check_min_account_balance,
        )
        print(details)
