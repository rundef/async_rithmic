from typing import Union
from datetime import datetime
import pytz

from rithmic.plants.base import BasePlant
import rithmic.protocol_buffers as pb
from rithmic.enums import DataType

class TickerPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.TICKER_PLANT

    async def get_front_month_contract(self, underlying_code: str, exchange_code: str) -> Union[str, None]:
        """
        Get the current Front Month Contract of an underlying code and exchange, eg ES and CME

        :param underlying_code: (str) valid underlying code
        :param exchange_code: (str) valid exchange code
        :return: (str) the front month futures contract
        """

        response = await self._send_and_recv(
            template_id=113,
            symbol=underlying_code,
            exchange=exchange_code,
            user_msg=[underlying_code]
        )
        return response.trading_symbol

    async def subscribe_to_market_data(
        self,
        security_code: str,
        exchange_code: str,
        data_type: int
    ):
        return await self._send_and_recv(
            template_id=100,
            symbol=security_code,
            exchange=exchange_code,
            request=pb.request_market_data_update_pb2.RequestMarketDataUpdate.Request.SUBSCRIBE,
            update_bits=data_type
        )

    async def unsubscribe_from_market_data(
        self,
        security_code: str,
        exchange_code: str,
        data_type: int
    ):
        return await self._send_and_recv(
            template_id=100,
            symbol=security_code,
            exchange=exchange_code,
            request=pb.request_market_data_update_pb2.RequestMarketDataUpdate.Request.UNSUBSCRIBE,
            update_bits=data_type
        )

    async def _process_message(self, message):
        response = self._convert_bytes_to_response(message)

        if response.template_id == 150:
            # Market data stream: Last Trade
            ts = '{0}.{1}'.format(response.ssboe, response.usecs)
            data = self._response_to_dict(response)
            data["datetime"] = datetime.fromtimestamp(float(ts), tz=pytz.utc)
            data["date_type"] = DataType.LAST_TRADE

            await self.client.on_tick.notify(data)

        elif response.template_id == 151:
            # Market data stream: Best Bid Offer
            ts = '{0}.{1}'.format(response.ssboe, response.usecs)
            data = self._response_to_dict(response)
            data["datetime"] = datetime.fromtimestamp(float(ts), tz=pytz.utc)
            data["date_type"] = DataType.BBO

            await self.client.on_tick.notify(data)

        else:
            print("UNHANDLED", response)
