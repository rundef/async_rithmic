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

        if len(self._subscriptions["pnl"]) > 0:
            await self.subscribe_to_pnl_updates()

    async def subscribe_to_pnl_updates(self):
        """
        Subscribe to instruments/accounts PNL updates
        """
        self._subscriptions["pnl"].add(1)

        for account in self._accounts:
            await self._send_request(
                template_id=400,
                fcm_id=self._fcm_id,
                ib_id=self._ib_id,
                account_id=account.account_id,
                request=pb.request_pnl_position_updates_pb2.RequestPnLPositionUpdates.Request.SUBSCRIBE
            )

    async def unsubscribe_from_pnl_updates(self):
        """
        Unsubscribe from instruments/accounts PNL updates
        """
        self._subscriptions["pnl"].discard(1)

        for account in self._accounts:
            await self._send_request(
                template_id=400,
                fcm_id=self._fcm_id,
                ib_id=self._ib_id,
                account_id=account.account_id,
                request=pb.request_pnl_position_updates_pb2.RequestPnLPositionUpdates.Request.UNSUBSCRIBE
            )

    async def list_positions(self, **kwargs):
        """
        Instrument PNL snapshots
        """
        return await self._send_and_collect(
            template_id=402,
            expected_response=dict(template_id=450, is_snapshot=True),
            **kwargs
        )

    async def list_account_summary(self, **kwargs):
        """
        Account PNL snapshots
        """
        return await self._send_and_collect(
            template_id=402,
            expected_response=dict(template_id=451, is_snapshot=True),
            **kwargs
        )

    async def _process_response(self, response):
        if await super()._process_response(response):
            return True

        if response.template_id == 450:
            # Instrument PNL position update
            await self.client.on_instrument_pnl_update.call_async(response)

        elif response.template_id == 451:
            # Account PNL position update
            await self.client.on_account_pnl_update.call_async(response)

        else:
            self.logger.warning(f"Unhandled inbound message with template_id={response.template_id}")
