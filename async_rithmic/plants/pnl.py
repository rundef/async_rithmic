from .base import BasePlant
from .. import protocol_buffers as pb

class PnlPlant(BasePlant):
    infra_type = pb.request_login_pb2.RequestLogin.SysInfraType.PNL_PLANT

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
        async with self.lock:
            for account in self._accounts:
                await self._send_request(
                    template_id=400,
                    fcm_id=self._fcm_id,
                    ib_id=self._ib_id,
                    account_id=account.account_id,
                    request=pb.request_pnl_position_updates_pb2.RequestPnLPositionUpdates.Request.SUBSCRIBE
                )

    async def list_positions(self, **kwargs):
        return await self._send_and_collect(
            template_id=402,
            expected_response=dict(template_id=450, is_snapshot=True),
            **kwargs
        )

    async def list_account_summary(self, **kwargs):
        return await self._send_and_collect(
            template_id=402,
            expected_response=dict(template_id=451, is_snapshot=True),
            **kwargs
        )
