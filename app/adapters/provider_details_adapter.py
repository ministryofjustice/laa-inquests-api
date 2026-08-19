import logging
import time

import httpx

from app.logging_utils import build_log_extra, duration_ms
from app.models.application.index import Address
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import ProviderDetailsRetrievalError

logger = logging.getLogger(__name__)


class ProviderDetailsAdapter(ProviderDetailsPort):
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key

    def get_firm_name(self, firm_code: str) -> str:
        started_at = time.perf_counter()
        try:
            url = f"{self.base_url}/api/v1/provider-firms/{firm_code}"
            response = httpx.get(
                url,
                headers={"X-Authorization": self.api_key},
            )

            response.raise_for_status()
            result = response.json()["firm"]["firmName"]
            logger.info(
                "Provider firm name lookup succeeded",
                extra=build_log_extra(
                    event="provider_details_firm_name_lookup_success",
                    route="provider-details:provider-firms",
                    method="GET",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                    firm_code=firm_code,
                ),
            )
            return result
        except httpx.HTTPError as exc:
            logger.error(
                "Provider firm name lookup failed",
                extra=build_log_extra(
                    event="provider_details_firm_name_lookup_failed",
                    route="provider-details:provider-firms",
                    method="GET",
                    duration_ms=duration_ms(started_at),
                    firm_code=firm_code,
                ),
            )
            raise ProviderDetailsRetrievalError(
                f"HTTP error occurred while retrieving provider details: {exc}"
            ) from exc
        except (KeyError, ValueError) as exc:
            logger.error(
                "Provider firm name lookup failed",
                extra=build_log_extra(
                    event="provider_details_firm_name_lookup_failed",
                    route="provider-details:provider-firms",
                    method="GET",
                    duration_ms=duration_ms(started_at),
                    firm_code=firm_code,
                ),
            )
            raise ProviderDetailsRetrievalError(
                f"Unexpected provider-firms response for firm {firm_code}"
            ) from exc

    def get_office_address(self, office_id: str) -> Address:
        started_at = time.perf_counter()
        try:
            url = f"{self.base_url}/api/v1/provider-offices/{office_id}"
            response = httpx.get(
                url,
                headers={"X-Authorization": self.api_key},
            )
            response.raise_for_status()

            address = Address(
                address_line_1=response.json()["office"]["addressLine1"],
                address_line_2=response.json()["office"]["addressLine2"],
                postcode=response.json()["office"]["postCode"],
                town_or_city=response.json()["office"]["city"],
                county=response.json()["office"]["county"],
            )
            logger.info(
                "Provider office address lookup succeeded",
                extra=build_log_extra(
                    event="provider_details_office_address_lookup_success",
                    route="provider-details:provider-offices",
                    method="GET",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                    office_id=office_id,
                ),
            )
            return address
        except httpx.HTTPError as exc:
            logger.error(
                "Provider office address lookup failed",
                extra=build_log_extra(
                    event="provider_details_office_address_lookup_failed",
                    route="provider-details:provider-offices",
                    method="GET",
                    duration_ms=duration_ms(started_at),
                    office_id=office_id,
                ),
            )
            raise ProviderDetailsRetrievalError(
                f"HTTP error occurred while retrieving provider details: {exc}"
            ) from exc
        except (KeyError, ValueError) as exc:
            logger.error(
                "Provider office address lookup failed",
                extra=build_log_extra(
                    event="provider_details_office_address_lookup_failed",
                    route="provider-details:provider-offices",
                    method="GET",
                    duration_ms=duration_ms(started_at),
                    office_id=office_id,
                ),
            )
            raise ProviderDetailsRetrievalError(
                f"Unexpected provider-offices response for office {office_id}"
            ) from exc

    def does_office_exist(self, office_id: str) -> None:
        try:
            self.get_office_address(office_id)
        except Exception:
            raise ProviderDetailsRetrievalError(
                f"Office id {office_id} does not exist in provider details API"
            )

    def get_firms_by_ids(self, firm_ids: list[str]) -> list[dict]:
        if not firm_ids:
            return []
        started_at = time.perf_counter()
        try:
            url = f"{self.base_url}/api/v1/provider-firms"
            response = httpx.post(
                url,
                json={"firmIds": firm_ids},
                headers={"X-Authorization": self.api_key},
            )
            response.raise_for_status()
            firms = response.json()["firms"]
            logger.info(
                "Provider firms batch lookup succeeded",
                extra=build_log_extra(
                    event="provider_details_firms_batch_lookup_success",
                    route="provider-details:provider-firms",
                    method="POST",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                    requested_count=len(firm_ids),
                    result_count=len(firms),
                ),
            )
            return firms
        except httpx.HTTPError as exc:
            logger.error(
                "Provider firms batch lookup failed",
                extra=build_log_extra(
                    event="provider_details_firms_batch_lookup_failed",
                    route="provider-details:provider-firms",
                    method="POST",
                    duration_ms=duration_ms(started_at),
                    requested_count=len(firm_ids),
                ),
            )
            raise ProviderDetailsRetrievalError(
                f"Failed to retrieve firms from provider details API: #{exc}"
            ) from exc
