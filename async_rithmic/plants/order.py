from .base import BasePlant
from ..enums import OrderType, OrderDuration, TransactionType
from ..exceptions import InvalidRequestError
from .. import protocol_buffers as pb

class OrderPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.ORDER_PLANT

    login_info = None
    trade_routes = None
    accounts = None

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

        responses = await self._send_and_collect(
            template_id=300,
            expected_response=dict(template_id=301),
            account_id=None,
        )
        response = self._first(responses)

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

        return await self._send_and_collect(
            template_id=302,
            expected_response=dict(template_id=303),
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            user_type=self.login_info["user_type"],
            account_id=None,
        )

    async def _list_trade_routes(self) -> list:
        """
        Returns list of trade routes configured for user
        """

        return await self._send_and_collect(
            template_id=310,
            expected_response=dict(template_id=311),
            subscribe_for_updates=True,
            account_id=None,
        )

    async def _subscribe_to_updates(self, **kwargs):
        for account in self.accounts:
            await self._send_and_collect(
                expected_response=dict(template_id=kwargs["template_id"] + 1),
                fcm_id=self.login_info["fcm_id"],
                ib_id=self.login_info["ib_id"],
                account_id=account.account_id,
                **kwargs
            )

    async def get_account_rms(self):
        return await self._send_and_collect(
            template_id=304,
            expected_response=dict(template_id=305),
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            user_type=self.login_info["user_type"],
            account_id=None,
        )

    async def get_product_rms(self, **kwargs):
        return await self._send_and_collect(
            template_id=306,
            expected_response=dict(template_id=307),
            **kwargs
        )

    async def list_orders(self, **kwargs):
        return await self._send_and_collect(
            template_id=320,
            expected_response=dict(template_id=352, is_snapshot=True),
            **kwargs
        )

    async def get_order(self, **kwargs):
        """
        Get an order by order_id (user-assigned id) or basket_id (rithmic-assigned id)
        """

        order_id = kwargs.get("order_id")
        basket_id = kwargs.get("basket_id")
        if not order_id and not basket_id:
            raise InvalidRequestError("Missing argument: order_id or basket_id")

        # Check if the user specified an account_id
        account_ids = []
        if kwargs.get("account_id"):
            account_ids.append(kwargs.get("account_id"))
        else:
            account_ids = [a.account_id for a in self.accounts]

        # Fetch order from each sub account
        for account_id in account_ids:
            orders = await self.list_orders(account_id=account_id)

            if order_id:
                orders = [o for o in orders if o.user_tag == order_id]
            if basket_id:
                orders = [o for o in orders if o.basket_id == basket_id]

            if orders:
                return orders[0]

        return None

    def _get_account_id(self, **kwargs):
        """
        Returns the account id if there's only one
        Else, check that it's passed in the kwargs and valid
        """
        if len(self.accounts) == 1:
            return self.accounts[0].account_id

        elif "account_id" not in kwargs:
            raise InvalidRequestError(f"Missing argument: account_id (possible values are: {','.join([a.account_id for a in self.accounts])})")

        else:
            matches = [
                a for a in self.accounts if a.account_id == kwargs["account_id"]
            ]
            if not matches:
                raise InvalidRequestError(f"Invalid account_id specified (possible values are: {','.join([a.account_id for a in self.accounts])})")
            return matches[0].account_id

    def _validate_price_fields(self, order_type, **kwargs):
        """
        Validates that the correct price fields are passed via kwargs for a given order type
        """

        required_price_fields = set()
        if order_type in [OrderType.STOP_LIMIT, OrderType.LIMIT_IF_TOUCHED]:
            required_price_fields.add("trigger_price")
            required_price_fields.add("price")

        elif order_type in [OrderType.STOP_MARKET, OrderType.MARKET_IF_TOUCHED]:
            required_price_fields.add("trigger_price")

        elif order_type == OrderType.LIMIT:
            required_price_fields.add("price")

        for key in required_price_fields:
            if key not in kwargs:
                raise InvalidRequestError(f"Missing argument: {key} is mandatory for this order type")

        return {
            key: kwargs[key]
            for key in required_price_fields
        }

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

        msg_kwargs = self._validate_price_fields(order_type, **kwargs)
        msg_kwargs["account_id"] = kwargs.pop("account_id", None)

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

        release_at = kwargs.pop("release_at", None)
        cancel_at = kwargs.pop("cancel_at", None)
        if release_at:
            ssboe, usecs = self._datetime_to_ssboe_usecs(release_at)
            msg_kwargs["release_at_ssboe"] = ssboe
            msg_kwargs["release_at_usecs"] = usecs
        if cancel_at:
            ssboe, usecs = self._datetime_to_ssboe_usecs(cancel_at)
            msg_kwargs["cancel_at_ssboe"] = ssboe
            msg_kwargs["cancel_at_usecs"] = usecs

        return await self._send_and_collect(
            template_id=template_id,
            expected_response=dict(template_id=template_id + 1),
            user_tag=order_id,
            symbol=symbol,
            exchange=exchange,
            price_type=order_type,
            quantity=qty,
            manual_or_auto=pb.request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL,
            transaction_type=transaction_type,
            duration=kwargs["duration"],
            **msg_kwargs
        )

    async def cancel_order(self, **kwargs):
        """
        Cancel an order by order_id (user-assigned id) or basket_id (rithmic-assigned id)
        """

        basket_id = kwargs.get("basket_id")
        account_id = kwargs.get("account_id")

        if not basket_id or not account_id:
            order = await self.get_order(**kwargs)
            if not order:
                raise Exception(f"Order not found: {kwargs}")

            basket_id = order.basket_id
            account_id = order.account_id

        return await self._send_and_recv(
            template_id=316,
            manual_or_auto=pb.request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            basket_id=basket_id,
            account_id=account_id,
        )

    async def modify_order(
        self,
        order_id: str,
        qty: int,
        order_type: OrderType,
        **kwargs
    ):
        order = await self.get_order(order_id=order_id, **kwargs)
        if not order:
            raise Exception(f"Order {order_id} not found")

        msg_kwargs = self._validate_price_fields(order_type, **kwargs)

        return await self._send_and_recv(
            template_id=314,
            fcm_id=self.login_info["fcm_id"],
            ib_id=self.login_info["ib_id"],
            manual_or_auto=pb.request_new_order_pb2.RequestNewOrder.OrderPlacement.MANUAL,
            account_id=order.account_id,
            basket_id=order.basket_id,
            symbol=order.symbol,
            exchange=order.exchange,
            quantity=qty,
            price_type=order_type,
            **msg_kwargs
        )

    async def show_order_history_dates(self):
        """
        Show Order History Dates
        """

        return await self._send_and_collect(
            template_id=318,
            expected_response=dict(template_id=319),
            account_id=None,
        )

    async def show_order_history_summary(self, date: str, **kwargs):
        """
        Show Order History Summary
        `date` should be in YYYYMMDD format
        """
        return await self._send_and_collect(
            template_id=324,
            date=date,
            expected_response=dict(template_id=352, is_snapshot=True),
            **kwargs
        )

    async def _process_response(self, response):
        if await super()._process_response(response):
            return True

        if response.template_id == 351:
            # Rithmic order notification
            await self.client.on_rithmic_order_notification.call_async(response)

        elif response.template_id == 352:
            # Exchange order notification
            await self.client.on_exchange_order_notification.call_async(response)

        elif response.template_id == 353:
            # Bracket update
            pass

        elif response.template_id == 317:
            # Cancel order
            pass

        else:
            self.logger.warning(f"Unhandled inbound message with template_id={response.template_id}")
