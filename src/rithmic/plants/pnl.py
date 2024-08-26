from rithmic.plants.base import BasePlant
import rithmic.protocol_buffers as pb
from rithmic.logger import logger

class PnlPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.PNL_PLANT

    async def _login(self):
        await super()._login()
        await self._fetch_login_info()
        await self._subscribe_to_position_updates()

    async def _subscribe_to_position_updates(self):
        for account in self.client.plants["order"].accounts:
            await self._send_and_recv(
                template_id=402,
                fcm_id=self.client.plants["order"].login_info["fcm_id"],
                ib_id=self.client.plants["order"].login_info["ib_id"],
                account_id=account.account_id,
            )

    async def _process_message(self, message):
        response = self._convert_bytes_to_response(message)

        print("UNHANDLED", response)
