from rithmic.plants.base import BasePlant, TEMPLATES_MAP
from rithmic.enums import OrderType, OrderDuration

import rithmic.protocol_buffers as pb

class OrderPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.ORDER_PLANT

    login_info = None
    trade_routes = None
    accounts = None

    async def _login(self):
        await super()._login()
        await self._fetch_login_info()

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
        self.accounts = await self._list_accounts()

    async def _list_accounts(self) -> list:
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

    async def get_account_rms(self):
        return await self._send_and_recv_many(
            template_id=304,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            user_type=self.login_info["user_type"]
        )

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
        security_code: str,
        exchange: str,
        qty: int,
        order_type: OrderType,
        is_buy: bool,
        **kwargs
    ):
        kwargs.setdefault("duration", OrderDuration.DAY)
        msg_kwargs = {}

        if order_type == OrderType.LIMIT:
            if "limit_price" not in kwargs:
                raise Exception(f"Limit price must be specified for LMT orders")

            msg_kwargs["price"] = kwargs["limit_price"]

        elif order_type == OrderType.STOP_MARKET:
            if "stop_price" not in kwargs:
                raise Exception(f"Stop price must be specified for STP orders")

            msg_kwargs["price"] = kwargs["stop_price"]

        msg_kwargs["account_id"] = self._get_account_id(**kwargs)

        # Get trade route
        filtered = [r for r in self.trade_routes if r.exchange == exchange]
        if len(filtered) == 0:
            raise Exception(f"No Valid Trade Route Exists for {exchange}")
        msg_kwargs["trade_route"] = filtered[0].trade_route

        return await self._send_and_recv(
            template_id=312,
            user_tag=order_id,
            symbol=security_code,
            exchange=exchange,
            price_type=order_type,
            quantity=qty,
            manual_or_auto=pb.request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL,
            transaction_type=pb.request_new_order_pb2.RequestNewOrder.TransactionType.BUY if is_buy else \
                pb.request_new_order_pb2.RequestNewOrder.TransactionType.SELL,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            duration=kwargs["duration"],
            **msg_kwargs
        )

    async def cancel_order(self, order_id: str, **kwargs):
        return await self._send_and_recv(
            template_id=316,
            manual_or_auto=pb.request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL,
            bracket_id=None, # TODO: keep a mapping of order_id -> bracket_id
            account_id=self._get_account_id(**kwargs)
        )

    async def modify_order(
        self,
        order_id: str,
        qty: int,
        order_type: OrderType,
        **kwargs
    ):
        msg_kwargs = {}

        if order_type == OrderType.LIMIT:
            if "limit_price" not in kwargs:
                raise Exception(f"Limit price must be specified for LMT orders")

            msg_kwargs["price"] = kwargs["limit_price"]

        elif order_type == OrderType.STOP_MARKET:
            if "stop_price" not in kwargs:
                raise Exception(f"Stop price must be specified for STP orders")

            msg_kwargs["price"] = kwargs["stop_price"]

        return await self._send_and_recv(
            template_id=314,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            manual_or_auto=pb.request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL,
            account_id=self._get_account_id(**kwargs),
            bracket_id=None,  # TODO: keep a mapping of order_id -> bracket_id
            # TODO: symbol, exchange
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
                    break
                else:
                    results.append(response)

        return results

    async def _process_message(self, message):
        response = self._convert_bytes_to_response(message)

        if response.template_id == 350:
            # Trade route
            print("PROCESSMSG TRADEROUTE", response)

        elif response.template_id == 351:
            # Rithmic order notification
            print("PROCESSMSG RITHMICNOTIF", response)

        elif response.template_id == 352:
            # Exchange order notification
            print("PROCESSMSG EXCHANGENOTIF", response)

        else:
            print("UNHANDLED", response)
