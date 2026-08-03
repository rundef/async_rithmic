from typing import Optional

from .base import BasePlant
from ..enums import SysInfraType, DataType, SearchPattern
from ..exceptions import RithmicErrorResponse
from .. import protocol_buffers as pb

class TickerPlant(BasePlant):
    infra_type = SysInfraType.TICKER_PLANT

    async def _login(self):
        await super()._login()

        for symbol, exchange, update_bits in self._subscriptions["market_data"]:
            await self.subscribe_to_market_data(symbol, exchange, update_bits)

        for symbol, exchange, depth_price in self._subscriptions["market_depth"]:
            await self.subscribe_to_market_depth(symbol, exchange, depth_price)

    async def list_exchanges(self):
        return await self._send_and_collect(
            template_id=342,
            user=self.credentials["user"],
            expected_response=dict(template_id=343),
            account_id=None,
        )

    async def get_front_month_contract(self, symbol: str, exchange: str) -> str:
        """
        Get the current Front Month Contract of an underlying code and exchange, eg ES and CME

        :param symbol: (str) valid symbol (e.g. ES)
        :param exchange: (str) valid exchange (e.g. CME)
        :return: (str) the front month futures contract
        :raises RithmicErrorResponse: if Rithmic returns no data (rp_code=7,
            typically during the maintenance window) or an empty trading_symbol.
        """

        template_id = self.get_template_id("RequestFrontMonthContract")
        resp_template_id = self.get_template_id("ResponseFrontMonthContract")

        responses = await self._send_and_collect(
            template_id=template_id,
            expected_response=dict(template_id=resp_template_id),
            symbol=symbol,
            exchange=exchange,
            account_id=None,
        )
        response = self._first(responses)
        if response is None or not response.trading_symbol:
            raise RithmicErrorResponse(
                f"Rithmic returned no front-month contract for {symbol}/{exchange} "
                "(empty response — often occurs during the maintenance window)"
            )
        return response.trading_symbol

    async def subscribe_to_market_data(
        self,
        symbol: str,
        exchange: str,
        data_type: DataType | int
    ):
        update_bits = data_type.value if isinstance(data_type, DataType) else int(data_type)

        sub = (symbol, exchange, update_bits)
        self._subscriptions["market_data"].add(sub)

        await self._send_request(
            template_id=100,
            symbol=symbol,
            exchange=exchange,
            request=pb.request_market_data_update_pb2.RequestMarketDataUpdate.Request.SUBSCRIBE,
            update_bits=update_bits,
        )

    async def unsubscribe_from_market_data(
        self,
        symbol: str,
        exchange: str,
        data_type: DataType | int
    ):
        update_bits = data_type.value if isinstance(data_type, DataType) else int(data_type)

        sub = (symbol, exchange, update_bits)
        self._subscriptions["market_data"].discard(sub)

        await self._send_request(
            template_id=100,
            symbol=symbol,
            exchange=exchange,
            request=pb.request_market_data_update_pb2.RequestMarketDataUpdate.Request.UNSUBSCRIBE,
            update_bits=update_bits,
        )

    async def search_symbols(
        self,
        search_text: str,
        exchange: Optional[str] = None,
        product_code: Optional[str] = None,
        instrument_type: int | None = None,
        pattern: int = SearchPattern.CONTAINS,
    ):
        """
        Search symbols

        :param search_text: (str)
        :param product_code: (str)
        :param exchange: (str)
        :param instrument_type: (InstrumentType)
        """

        params = {
            "search_text": search_text,
            "exchange": exchange,
            "product_code": product_code,
            "instrument_type": instrument_type,
            "pattern": pattern,
        }

        return await self._send_and_collect(
            template_id=109,
            expected_response=dict(template_id=110),
            **{key: value for key, value in params.items() if value is not None},
            account_id=None,
        )

    async def get_product_codes(
        self,
        exchange: str,
        toi_products_only: bool = True,
    ):
        """
        Returns the product codes
        """

        return await self._send_and_collect(
            template_id=111,
            expected_response=dict(template_id=112),
            exchange=exchange,
            give_toi_products_only=toi_products_only,
            account_id=None,
        )

    async def get_auxilliary_reference_data(
        self,
        symbol: str,
        exchange: str,
    ):
        return await self._send_and_collect(
            template_id=121,
            expected_response=dict(template_id=122),
            symbol=symbol,
            exchange=exchange,
            account_id=None,
        )

    async def request_market_depth(
        self,
        symbol: str,
        exchange: str,
        depth_price: float
    ):
        """
        Request order book data for a given price
        """
        responses = await self._send_and_collect(
            template_id=115,
            expected_response=dict(template_id=116),
            symbol=symbol,
            exchange=exchange,
            depth_price=depth_price,
            account_id=None,
        )
        return responses[0] if responses else None

    async def subscribe_to_market_depth(
        self,
        symbol: str,
        exchange: str,
        depth_price: float
    ):
        """
        Subscribes to market depth updates (L2 data) for a given price
        """

        sub = (symbol, exchange, depth_price)
        self._subscriptions["market_depth"].add(sub)

        await self._send_request(
            template_id=117,
            symbol=symbol,
            exchange=exchange,
            depth_price=depth_price,
            request=pb.request_depth_by_order_updates_pb2.RequestDepthByOrderUpdates.Request.SUBSCRIBE,
        )

    async def unsubscribe_from_market_depth(
        self,
        symbol: str,
        exchange: str,
        depth_price: float
    ):
        """
        Unsubscribes from market depth updates (L2 data) for a given price
        """

        sub = (symbol, exchange, depth_price)
        self._subscriptions["market_depth"].discard(sub)

        await self._send_request(
            template_id=117,
            symbol=symbol,
            exchange=exchange,
            depth_price=depth_price,
            request=pb.request_depth_by_order_updates_pb2.RequestDepthByOrderUpdates.Request.UNSUBSCRIBE,
        )

    async def _process_response(self, response):
        if await super()._process_response(response):
            return True

        if response.template_id == 101:
            # Market data update response
            pass

        elif response.template_id == 118:
            # Market depth data update response
            pass

        elif response.template_id == 150:
            # Market data stream: Last Trade
            data = self._response_to_dict(response)
            data["datetime"] = self._ssboe_usecs_to_datetime(response.ssboe, response.usecs)
            data["data_type"] = DataType.LAST_TRADE

            await self.client.on_tick.call_async(data)

        elif response.template_id == 151:
            # Market data stream: Best Bid Offer
            data = self._response_to_dict(response)
            data["datetime"] = self._ssboe_usecs_to_datetime(response.ssboe, response.usecs)
            data["data_type"] = DataType.BBO

            await self.client.on_tick.call_async(data)

        elif response.template_id == 156:
            # Market data stream: Order Book
            await self.client.on_order_book.call_async(response)

        elif response.template_id == 160:
            # Market depth data stream
            await self.client.on_market_depth.call_async(response)

        else:
            self.logger.warning(f"Unhandled inbound message with template_id={response.template_id}")
