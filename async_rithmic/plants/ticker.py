from typing import Union

from .base import BasePlant
from ..enums import DataType, SearchPattern
from ..logger import logger
from .. import protocol_buffers as pb

class TickerPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.TICKER_PLANT

    async def get_front_month_contract(self, symbol: str, exchange: str) -> Union[str, None]:
        """
        Get the current Front Month Contract of an underlying code and exchange, eg ES and CME

        :param symbol: (str) valid symbol (e.g. ES)
        :param exchange: (str) valid exchange (e.g. CME)
        :return: (str) the front month futures contract
        """

        responses = await self._send_and_collect(
            template_id=113,
            expected_response=dict(template_id=114),
            symbol=symbol,
            exchange=exchange,
            account_id=None,
        )
        response = self._first(responses)
        return response.trading_symbol if response else None

    async def subscribe_to_market_data(
        self,
        symbol: str,
        exchange: str,
        data_type: DataType
    ):
        async with self.lock:
            await self._send_request(
                template_id=100,
                symbol=symbol,
                exchange=exchange,
                request=pb.request_market_data_update_pb2.RequestMarketDataUpdate.Request.SUBSCRIBE,
                update_bits=data_type.value
            )

    async def unsubscribe_from_market_data(
        self,
        symbol: str,
        exchange: str,
        data_type: DataType
    ):
        async with self.lock:
            await self._send_request(
                template_id=100,
                symbol=symbol,
                exchange=exchange,
                request=pb.request_market_data_update_pb2.RequestMarketDataUpdate.Request.UNSUBSCRIBE,
                update_bits=data_type.value
            )

    async def search_symbols(self, search_text, **kwargs):
        """
        Search symbols

        :param search_text: (str)
        :param product_code: (str)
        :param exchange: (str)
        :param instrument_type: (InstrumentType)
        """

        kwargs.setdefault("pattern", SearchPattern.CONTAINS)

        return await self._send_and_collect(
            template_id=109,
            expected_response=dict(template_id=110),
            search_text=search_text,
            account_id=None,
            **kwargs
        )

    async def _process_response(self, response):
        if await super()._process_response(response):
            return True

        if response.template_id == 101:
            # Market data update response
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

        else:
            self.logger.warning(f"Unhandled inbound message with template_id={response.template_id}")
