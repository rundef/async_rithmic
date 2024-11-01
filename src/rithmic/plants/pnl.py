import asyncio

from rithmic.plants.base import BasePlant
import rithmic.protocol_buffers as pb
from rithmic.logger import logger

class PnlPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.PNL_PLANT

    _position_list = []
    _position_list_event = None
    _position_template_id = None

    @property
    def _accounts(self):
        return self.client.plants["order"].accounts

    @property
    def _fcm_id(self):
        return self.client.plants["order"].login_info["fcm_id"]

    @property
    def _ib_id(self):
        return self.client.plants["order"].login_info["ib_id"]

    async def _login(self):
        await super()._login()
        await self._subscribe_to_position_updates()

    async def _subscribe_to_position_updates(self):
        for account in self._accounts:
            await self._send_and_recv(
                template_id=400,
                fcm_id=self._fcm_id,
                ib_id=self._ib_id,
                account_id=account.account_id,
                request=pb.request_pnl_position_updates_pb2.RequestPnLPositionUpdates.Request.SUBSCRIBE
            )

    async def _list_objects(self, template_id, response_template_id, **kwargs):
        self._position_list = []
        self._position_list_event = asyncio.Event()
        self._position_template_id = response_template_id

        account_id = self.client.plants["order"]._get_account_id(**kwargs)
        kwargs.pop("account_id", None)

        async with self.lock:
            await self._send_request(
                template_id=template_id,
                fcm_id=self._fcm_id,
                ib_id=self._ib_id,
                account_id=account_id,
                **kwargs
            )

        await self._position_list_event.wait()
        return self._position_list

    async def list_positions(self, **kwargs):
        return await self._list_objects(template_id=402, response_template_id=450, **kwargs)

    async def list_account_summary(self, **kwargs):
        return await self._list_objects(template_id=402, response_template_id=451, **kwargs)

    async def _process_message(self, message):
        response = self._convert_bytes_to_response(message)

        if response.template_id == 403:
            # Position snapshot Response
            self._position_list_event.set()

            if len(response.rp_code) and response.rp_code[0] != '0':
                logger.exception(f"Rithmic returned an error after request: {', '.join(response.rp_code)}")

        elif response.template_id in [450, 451]:
            if response.is_snapshot and response.template_id == self._position_template_id:
                self._position_list.append(response)

        else:
            logger.warning(f"Pnl plant: unhandled inbound message with template_id={response.template_id}")

