import logging

from app.logging_utils import build_log_extra
from app.ports.provider_details_port import ProviderDetailsPort

logger = logging.getLogger(__name__)


class ListProviderOfficesUseCase:
    def __init__(self, provider_details_port: ProviderDetailsPort) -> None:
        self.provider_details_port = provider_details_port

    def execute(self, firm_id: str) -> list[dict]:
        provider_offices = self.provider_details_port.get_provider_offices_by_firm_id(
            firm_id
        )
        logger.info(
            "Provider offices listed",
            extra=build_log_extra(
                event="provider_offices_list_completed",
                firm_id=firm_id,
                result_count=len(provider_offices),
            ),
        )
        return provider_offices
