from typing import Literal

from .base import BasePlant
from ..enums import SysInfraType


class RepositoryPlant(BasePlant):
    infra_type = SysInfraType.REPOSITORY_PLANT

    async def list_unaccepted_agreements(self) -> list:
        """
        Return list of unaccepted agreements
        """

        return await self._send_and_collect(
            template_id=500,
            expected_response=dict(template_id=501),
            account_id=None,
        )

    async def list_accepted_agreements(self) -> list:
        """
        Return list of accepted agreements
        """

        return await self._send_and_collect(
            template_id=502,
            expected_response=dict(template_id=503),
            account_id=None,
        )
    
    async def get_agreement(self, agreement_id: str):
        """
        Return an agreement
        """

        responses = await self._send_and_collect(
            template_id=506,
            expected_response=dict(template_id=507),
            agreement_id=agreement_id,
            account_id=None,
        )
        return self._first(responses)

    async def accept_agreement(
        self,
        agreement_id: str,
        market_data_usage_capacity: Literal["Professional", "Non-Professional"]
    ):
        """
        Accept an agreement
        """

        return await self._send_and_collect(
            template_id=504,
            expected_response=dict(template_id=505),
            agreement_id=agreement_id,
            market_data_usage_capacity=market_data_usage_capacity,
            account_id=None,
        )
