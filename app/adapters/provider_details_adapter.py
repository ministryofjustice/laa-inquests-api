import logging
import time

import httpx

from app.logging_utils import build_log_extra, duration_ms
from app.models.application.index import Address
from app.ports.provider_details_port import ProviderDetailsPort
from app.use_cases.exceptions import (
    ProviderDetailsRetrievalError,
    ProviderOfficeNotFoundError,
)

logger = logging.getLogger(__name__)


class ProviderDetailsAdapter(ProviderDetailsPort):
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key

    def get_firm_name(self, firm_code: str, office_id: str) -> str | None:
        started_at = time.perf_counter()
        try:
            url = f"{self.base_url}/api/v1/provider-firms/{firm_code}"
            response = httpx.get(
                url,
                headers={"X-Authorization": self.api_key},
            )

            if response.status_code == 204:
                # 204 is ambiguous upstream: firm not found, or firm has no offices.
                # Fall back to the office lookup to recover a firm name and confirm office validity.
                logger.info(
                    f"No offices found for firm {firm_code}, falling back to office lookup",
                    extra=build_log_extra(
                        event="provider_details_firm_name_fallback_used",
                        route="provider-details:provider-firms",
                        method="GET",
                        status_code=response.status_code,
                        duration_ms=duration_ms(started_at),
                        firm_code=firm_code,
                        office_id=office_id,
                    ),
                )
                return self._get_firm_name_from_office(office_id, firm_code)

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
            logger.exception(
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
            logger.exception(
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

    def _get_firm_name_from_office(self, office_id: str, firm_code: str) -> str | None:
        started_at = time.perf_counter()
        try:
            url = f"{self.base_url}/api/v1/provider-offices/{office_id}"
            response = httpx.get(
                url,
                headers={"X-Authorization": self.api_key},
            )

            if response.status_code == 204:
                # Both the firm and office lookups came back empty: genuinely not found.
                raise ProviderOfficeNotFoundError(
                    f"Office {office_id} details not found for firm {firm_code}"
                )

            response.raise_for_status()
            result = response.json()["firm"]["firmName"]
            logger.info(
                "Provider firm name office fallback succeeded",
                extra=build_log_extra(
                    event="provider_details_firm_name_office_fallback_success",
                    route="provider-details:provider-offices",
                    method="GET",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                    office_id=office_id,
                ),
            )
            return result
        except httpx.HTTPError as exc:
            logger.exception(
                "Provider firm name office fallback failed",
                extra=build_log_extra(
                    event="provider_details_firm_name_office_fallback_failed",
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
            logger.exception(
                "Provider firm name office fallback failed",
                extra=build_log_extra(
                    event="provider_details_firm_name_office_fallback_failed",
                    route="provider-details:provider-offices",
                    method="GET",
                    duration_ms=duration_ms(started_at),
                    office_id=office_id,
                ),
            )
            raise ProviderDetailsRetrievalError(
                f"Unexpected provider-offices response for office {office_id}"
            ) from exc

    def get_office_address(self, office_id: str) -> Address:
        started_at = time.perf_counter()
        try:
            url = f"{self.base_url}/api/v1/provider-offices/{office_id}"
            response = httpx.get(
                url,
                headers={"X-Authorization": self.api_key},
            )

            if response.status_code == 204:
                raise ProviderOfficeNotFoundError(f"Office {office_id} not found")

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

    def get_provider_offices_by_firm_id(
        self, firm_id: str, candidate_office_codes: frozenset[str]
    ) -> list[dict]:
        started_at = time.perf_counter()
        try:
            url = f"{self.base_url}/api/v1/provider-firms/{firm_id}/provider-offices"
            response = httpx.get(
                url,
                headers={"X-Authorization": self.api_key},
            )

            if response.status_code == 204:
                # 204 is ambiguous upstream: firm not found, or firm has no offices.
                # Doesn't mean the user's own known offices are invalid, so resolve them individually.
                logger.info(
                    f"No offices found for firm {firm_id}, falling back to per-office lookups",
                    extra=build_log_extra(
                        event="provider_details_offices_by_firm_fallback_used",
                        route="provider-details:provider-firms:provider-offices",
                        method="GET",
                        status_code=response.status_code,
                        duration_ms=duration_ms(started_at),
                        firm_id=firm_id,
                        candidate_office_count=len(candidate_office_codes),
                    ),
                )
                return self._get_offices_from_candidates(candidate_office_codes)

            response.raise_for_status()

            offices = response.json()["offices"]
            result = [
                {
                    "office_code": office["firmOfficeCode"],
                    "address": {
                        "address_line_1": office.get("addressLine1", ""),
                        "address_line_2": office.get("addressLine2", ""),
                        "town_or_city": office.get("city", ""),
                        "county": office.get("county", ""),
                        "postcode": office.get("postCode", ""),
                    },
                }
                for office in offices
            ]

            logger.info(
                "Provider offices by firm lookup succeeded",
                extra=build_log_extra(
                    event="provider_details_provider_offices_lookup_success",
                    route="provider-details:provider-firms:provider-offices",
                    method="GET",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                    firm_id=firm_id,
                    result_count=len(result),
                ),
            )
            return result
        except httpx.HTTPError as exc:
            logger.exception(
                "Provider offices by firm lookup failed",
                extra=build_log_extra(
                    event="provider_details_provider_offices_lookup_failed",
                    route="provider-details:provider-firms:provider-offices",
                    method="GET",
                    duration_ms=duration_ms(started_at),
                    firm_id=firm_id,
                ),
            )
            raise ProviderDetailsRetrievalError(
                f"HTTP error occurred while retrieving provider details: {exc}"
            ) from exc
        except (KeyError, TypeError, ValueError) as exc:
            logger.exception(
                "Provider offices by firm lookup failed",
                extra=build_log_extra(
                    event="provider_details_provider_offices_lookup_failed",
                    route="provider-details:provider-firms:provider-offices",
                    method="GET",
                    duration_ms=duration_ms(started_at),
                    firm_id=firm_id,
                ),
            )
            raise ProviderDetailsRetrievalError(
                f"Unexpected provider-offices response for firm {firm_id}"
            ) from exc

    def _get_offices_from_candidates(self, office_codes: frozenset[str]) -> list[dict]:
        results = []
        for office_code in office_codes:
            try:
                address = self.get_office_address(office_code)
            except ProviderDetailsRetrievalError:
                # Best-effort: a single office failing (genuinely not found, or a
                # transient error) shouldn't hide the caller's other valid offices.
                logger.warning(
                    "Skipping office in candidate fallback lookup",
                    extra=build_log_extra(
                        event="provider_details_offices_by_firm_fallback_candidate_skipped",
                        route="provider-details:provider-offices",
                        method="GET",
                        office_code=office_code,
                    ),
                )
                continue
            results.append(
                {
                    "office_code": office_code,
                    "address": {
                        "address_line_1": address.address_line_1,
                        "address_line_2": address.address_line_2 or "",
                        "town_or_city": address.town_or_city,
                        "county": address.county or "",
                        "postcode": address.postcode,
                    },
                }
            )
        return results
