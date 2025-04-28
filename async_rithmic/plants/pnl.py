import asyncio
import uuid
from collections import defaultdict

from .base import BasePlant
from ..logger import logger
from .. import protocol_buffers as pb

class PnlPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.PNL_PLANT

    _object_list = defaultdict(list)
    _object_list_event = defaultdict(asyncio.Event)
    _object_response_template_id = {}
    _object_account_to_request_id = {}

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
        account_id = self.client.plants["order"]._get_account_id(**kwargs)
        kwargs.pop("account_id", None)

        if account_id in self._object_account_to_request_id:
            raise Exception(
                f"There's already an active request for account_id={account_id}. "
                "Cannot send simultaneous requests for the same account."
            )

        request_id = str(uuid.uuid4())

        self._object_response_template_id[request_id] = response_template_id
        self._object_account_to_request_id[account_id] = request_id

        async with self.lock:
            await self._send_request(
                user_msg=request_id,
                template_id=template_id,
                fcm_id=self._fcm_id,
                ib_id=self._ib_id,
                account_id=account_id,
                **kwargs
            )

        await self._object_list_event[request_id].wait()

        # Clean up
        del self._object_list_event[request_id]
        del self._object_response_template_id[request_id]
        del self._object_account_to_request_id[account_id]

        return self._object_list.pop(request_id, [])

    async def list_positions(self, **kwargs):
        return await self._list_objects(template_id=402, response_template_id=450, **kwargs)

    async def list_account_summary(self, **kwargs):
        return await self._list_objects(template_id=402, response_template_id=451, **kwargs)

    async def _process_response(self, response):
        if response.template_id == 403:
            # Position snapshot Response
            request_id = response.user_msg[0]

            if request_id in self._object_list_event:
                self._object_list_event[request_id].set()
            else:
                logger.error(f"Unknown request id = {request_id}")

            if len(response.rp_code) and response.rp_code[0] != '0':
                logger.exception(f"Rithmic returned an error after request: {', '.join(response.rp_code)}")

        elif response.template_id in [450, 451]:
            if response.is_snapshot:
                request_id = self._object_account_to_request_id[response.account_id]

                if response.template_id == self._object_response_template_id[request_id]:
                    self._object_list[request_id].append(response)

        else:
            logger.warning(f"Pnl plant: unhandled inbound message with template_id={response.template_id}")
