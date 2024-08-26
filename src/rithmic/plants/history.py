from datetime import datetime
import pytz

from rithmic.plants.base import BasePlant
import rithmic.protocol_buffers as pb
from rithmic.logger import logger

class HistoryPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.HISTORY_PLANT

    async def get_historical_tick_data(
        self,
        symbol: str,
        exchange: str,
        start_time: datetime,
        end_time: datetime
    ):
        """
        Creates and sends request for download of tick data for security/exchange over time period

        :param request_id: (str) generated request id used for processing as messages come in
        :param symbol: (str) valid security code (e.g. ES)
        :param exchange: (str) valid exchange code (e.g. CME)
        :param start_time: (dt) start time as datetime in utc
        :param end_time: (dt) end time as datetime in utc
        :return: None
        """

        return await self._send_and_recv(
            template_id=206,
            user_msg=symbol,
            symbol=symbol,
            exchange=exchange,
            bar_type=pb.request_tick_bar_replay_pb2.RequestTickBarReplay.BarType.TICK_BAR,
            bar_type_specifier="1",
            bar_sub_type=pb.request_tick_bar_replay_pb2.RequestTickBarReplay.BarSubType.REGULAR,
            start_index=int(start_time.timestamp()),
            finish_index=int(end_time.timestamp()),
        )

    async def _process_message(self, message):
        response = self._convert_bytes_to_response(message)

        if response.template_id == 207:
            # Historical tick data
            is_last_bar = response.rp_code == ['0'] or response.rq_handler_rp_code == []
            if is_last_bar:
                return

            ts = '{0}.{1}'.format(response.data_bar_ssboe[0], response.data_bar_usecs[0])
            data = self._response_to_dict(response)
            data["datetime"] = datetime.fromtimestamp(float(ts), tz=pytz.utc)

            await self.client.on_historical_tick.notify(data)

        else:
            print("UNHANDLED", response)
