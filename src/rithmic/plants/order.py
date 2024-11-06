import asyncio

from rithmic.plants.base import BasePlant, TEMPLATES_MAP
from rithmic.enums import OrderType, OrderDuration, TransactionType
import rithmic.protocol_buffers as pb
from rithmic.logger import logger

class OrderPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.ORDER_PLANT

    login_info = None
    trade_routes = None
    accounts = None

    _order_list = []
    _order_list_event = None

    async def _login(self):
        await super()._login()
        await self._fetch_login_info()

        # Order updates
        await self._subscribe_to_updates(template_id=308)
        # Bracket updates
        #await self._subscribe_to_updates(template_id=336)

    async def _fetch_login_info(self):
        """
        Fetch extended login details for order management, accounts, trade routes etc
        """

        response = await self._send_and_recv(template_id=300)

        self.login_info = dict(
            fcm_id=response.fcm_id,
            ib_id=response.ib_id,
            user_type=response.user_type,
        )
        self.trade_routes = await self._list_trade_routes()
        self.accounts = await self.list_accounts()

    async def list_accounts(self) -> list:
        """
        Return list of user's accounts
        """

        return await self._send_and_recv_many(
            template_id=302,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            user_type=self.login_info["user_type"]
        )

    async def _list_trade_routes(self) -> list:
        """
        Returns list of trade routes configured for user
        """

        return await self._send_and_recv_many(
            template_id=310,
            subscribe_for_updates=True,
        )

    async def _subscribe_to_updates(self, **kwargs):
        for account in self.accounts:
            await self._send_and_recv(
                fcm_id=self.login_info["fcm_id"],
                ib_id=self.login_info["ib_id"],
                account_id=account.account_id,
                **kwargs
            )

    async def get_account_rms(self):
        return await self._send_and_recv_many(
            template_id=304,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            user_type=self.login_info["user_type"],
        )

    async def get_product_rms(self, **kwargs):
        return await self._send_and_recv_many(
            template_id=306,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            account_id=self._get_account_id(**kwargs),
        )

    async def list_orders(self, **kwargs):
        self._order_list = []
        self._order_list_event = asyncio.Event()

        async with self.lock:
            await self._send_request(
                template_id=320,
                fcm_id=self.login_info["fcm_id"],
                ib_id=self.login_info["ib_id"],
                account_id=self._get_account_id(**kwargs)
            )

        await self._order_list_event.wait()
        return self._order_list

    async def get_order(self, order_id: str, **kwargs):
        orders = await self.list_orders(**kwargs)
        orders = [o for o in orders if o.user_tag == order_id]
        return orders[0] if orders else None

    def _get_account_id(self, **kwargs):
        if len(self.accounts) == 1:
            return self.accounts[0].account_id

        elif "account_id" not in kwargs:
            raise Exception(f"You must specify an account_id for the order: {[a.account_id for a in self.accounts]}")

        else:
            matches = [
                a for a in self.accounts if a.account_id == kwargs["account_id"]
            ]
            if not matches:
                raise Exception(f"Account {kwargs['account_id']} not found")
            return matches[0].account_id

    async def submit_order(
        self,
        order_id: str,
        symbol: str,
        exchange: str,
        qty: int,
        transaction_type: TransactionType,
        order_type: OrderType,
        **kwargs
    ):
        kwargs.setdefault("duration", OrderDuration.DAY)
        msg_kwargs = {}

        if order_type in [OrderType.LIMIT, OrderType.STOP_MARKET]:
            if "price" not in kwargs:
                raise Exception("Price must be specified for this order type")

            msg_kwargs["price"] = kwargs["price"]

        msg_kwargs["account_id"] = self._get_account_id(**kwargs)

        # Get trade route
        filtered = [r for r in self.trade_routes if r.exchange == exchange]
        if len(filtered) == 0:
            raise Exception(f"No Valid Trade Route Exists for {exchange}")
        msg_kwargs["trade_route"] = filtered[0].trade_route

        template_id = 312
        # Stop or target specified: use template_id 330 for bracket orders
        if "stop_ticks" in kwargs:
            template_id = 330
            msg_kwargs["stop_ticks"] = kwargs["stop_ticks"]
            msg_kwargs["stop_quantity"] = qty
            msg_kwargs["bracket_type"] = pb.request_bracket_order_pb2.RequestBracketOrder.BracketType.STOP_ONLY_STATIC
        if "target_ticks" in kwargs:
            template_id = 330
            msg_kwargs["target_ticks"] = kwargs["target_ticks"]
            msg_kwargs["target_quantity"] = qty
            msg_kwargs["bracket_type"] = pb.request_bracket_order_pb2.RequestBracketOrder.BracketType.TARGET_AND_STOP_STATIC \
                if "stop_ticks" in kwargs else pb.request_bracket_order_pb2.RequestBracketOrder.BracketType.TARGET_ONLY_STATIC
        if template_id == 330:
            msg_kwargs["user_type"] = self.login_info["user_type"]

        return await self._send_and_recv_many(
            template_id=template_id,
            user_tag=order_id,
            symbol=symbol,
            exchange=exchange,
            price_type=order_type,
            quantity=qty,
            manual_or_auto=pb.request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL,
            transaction_type=transaction_type,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            duration=kwargs["duration"],
            **msg_kwargs
        )

    async def cancel_order(self, order_id: str, **kwargs):
        order = await self.get_order(order_id, **kwargs)
        if not order:
            raise Exception(f"Order {order_id} not found")

        return await self._send_and_recv_many(
            template_id=316,
            manual_or_auto=pb.request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            basket_id=order.basket_id,
            account_id=order.account_id,
        )

    async def modify_order(
        self,
        order_id: str,
        qty: int,
        order_type: OrderType,
        **kwargs
    ):
        order = await self.get_order(order_id, **kwargs)
        if not order:
            raise Exception(f"Order {order_id} not found")

        msg_kwargs = {}

        if order_type in [OrderType.LIMIT, OrderType.STOP_MARKET]:
            if "price" not in kwargs:
                raise Exception("Price must be specified for this order type")

            msg_kwargs["price"] = kwargs["price"]

        return await self._send_and_recv(
            template_id=314,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            manual_or_auto=pb.request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL,
            account_id=self._get_account_id(**kwargs),
            basket_id=order.basket_id,
            symbol=order.symbol,
            exchange=order.exchange,
            quantity=qty,
            price_type=order_type,
            **msg_kwargs
        )

    async def _send_and_recv_many(self, **kwargs):
        """
        Sends a request to the API and decode the response
        """
        template_id = kwargs["template_id"]

        if template_id not in TEMPLATES_MAP:
            raise Exception(f"Unknown request template id: {template_id}")

        request = TEMPLATES_MAP[template_id]()
        for k, v in kwargs.items():
            self._set_pb_field(request, k, v)

        results = []
        async with self.lock:
            await self._send(self._convert_request_to_bytes(request))

            while True:
                buffer = await self._recv()
                response = self._convert_bytes_to_response(buffer)

                if len(response.rp_code) > 0:
                    if response.rp_code[0] != '0':
                        raise Exception(f"Server returned an error after request {template_id}: {', '.join(response.rp_code)}")

                    break
                else:
                    results.append(response)

        return results

    async def _process_message(self, message):
        response = self._convert_bytes_to_response(message)

        if response.template_id == 321:
            # Show Orders Response
            self._order_list_event.set()

        elif response.template_id == 351:
            # Rithmic order notification
            await self.client.on_rithmic_order_notification.notify(response)

        elif response.template_id == 352:
            # Exchange order notification
            if response.is_snapshot:
                self._order_list.append(response)
            else:
                await self.client.on_exchange_order_notification.notify(response)

        elif response.template_id == 353:
            # Bracket update
            pass

        else:
            logger.warning(f"Order plant: unhandled inbound message with template_id={response.template_id}")
