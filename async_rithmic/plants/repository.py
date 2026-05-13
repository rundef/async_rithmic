from typing import List

from .base import BasePlant
from ..enums import SysInfraType


class RepositoryPlant(BasePlant):
    infra_type = SysInfraType.REPOSITORY_PLANT

    async def list_unaccepted_agreements(self) -> List:
        """
        Return list of unaccepted agreements
        """

        template_id = self.get_template_id("RequestListUnacceptedAgreements")
        resp_template_id = self.get_template_id("ResponseListUnacceptedAgreements")

        return await self._send_and_collect(
            template_id=template_id,
            expected_response=dict(template_id=resp_template_id),
            account_id=None,
        )

    async def list_accepted_agreements(self) -> List:
        """
        Return list of accepted agreements
        """

        template_id = self.get_template_id("RequestListAcceptedAgreements")
        resp_template_id = self.get_template_id("ResponseListAcceptedAgreements")

        return await self._send_and_collect(
            template_id=template_id,
            expected_response=dict(template_id=resp_template_id),
            account_id=None,
        )
    
    async def get_agreement(self, agreement_id: str):
        """
        Return an agreement
        """

        template_id = self.get_template_id("RequestShowAgreement")
        resp_template_id = self.get_template_id("ResponseShowAgreement")

        responses = await self._send_and_collect(
            template_id=template_id,
            expected_response=dict(template_id=resp_template_id),
            agreement_id=agreement_id,
            account_id=None,
        )
        return self._first(responses)
