import logging
import re
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import httpx

from app.logging_utils import build_log_extra, duration_ms
from app.models.application.index import (
    SDSUploadClaimEvidenceResponse,
    SDSUploadCoronersLetterResponse,
)
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    ClaimEvidenceDeleteError,
    ClaimEvidenceUploadError,
    CoronersLetterDeleteError,
    CoronersLetterUploadError,
    InvalidClaimEvidenceDocumentIdError,
    InvalidCoronersLetterDocumentIdError,
    SDSClaimEvidenceRetrievalError,
    SDSLetterRetrievalError,
)

logger = logging.getLogger(__name__)


class SdsAdapter(SdsPort):
    def __init__(
        self,
        base_url: str,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        scope: str,
    ) -> None:
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.token: str | None = None
        self.token_expiry: float = 0.0

    def _get_token(self) -> str:
        if self.token and time.time() < self.token_expiry:
            return self.token
        started_at = time.perf_counter()
        response = httpx.post(
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
            },
        )
        if response.status_code != 200:
            logger.error(
                "SDS token acquisition failed",
                extra=build_log_extra(
                    event="sds_token_acquisition_failed",
                    route="sds:oauth2/token",
                    method="POST",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            raise httpx.HTTPStatusError(
                f"Failed to retrieve sds token. API status code: {response.status_code}",
                request=response.request,
                response=response,
            )
        data = response.json()
        self.token = data["access_token"]

        timeout_buffer = 60  # minute
        self.token_expiry = time.time() + data["expires_in"] - timeout_buffer
        return self.token

    def virus_check_coroners_letter(
        self, coroners_letter: bytes, file_name: str
    ) -> bool:
        started_at = time.perf_counter()
        try:
            token = self._get_token()
            response = httpx.put(
                f"{self.base_url}/virus_check_file",
                files={
                    "file": (
                        file_name,
                        coroners_letter,
                        "application/octet-stream",
                    )
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            logger.error(
                "SDS coroners letter virus check failed",
                extra=build_log_extra(
                    event="sds_coroners_letter_virus_check_failed",
                    route="sds:virus_check_file",
                    method="PUT",
                    status_code=status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            raise CoronersLetterUploadError(
                f"Failed to perform virus check due to a network error: {exc}"
            ) from exc

        if response.status_code == 200:
            logger.info(
                "SDS coroners letter virus check passed",
                extra=build_log_extra(
                    event="sds_coroners_letter_virus_check_passed",
                    route="sds:virus_check_file",
                    method="PUT",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            return True
        elif response.status_code == 400:
            logger.warning(
                "SDS coroners letter virus check failed",
                extra=build_log_extra(
                    event="sds_coroners_letter_virus_check_failed",
                    route="sds:virus_check_file",
                    method="PUT",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            return False
        else:
            logger.error(
                "SDS coroners letter virus check failed",
                extra=build_log_extra(
                    event="sds_coroners_letter_virus_check_failed",
                    route="sds:virus_check_file",
                    method="PUT",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            raise CoronersLetterUploadError(
                f"Failed to perform virus check. API status code: {response.status_code}"
            )

    def save_coroners_letter(
        self, coroners_letter: bytes, file_name: str
    ) -> SDSUploadCoronersLetterResponse:
        unique_file_name, status = self._save_file(
            file_content=coroners_letter,
            file_name=file_name,
            file_kind="coroners_letter",
        )
        return SDSUploadCoronersLetterResponse(
            sds_file_name=unique_file_name,
            status=status,
        )

    def virus_check_claim_evidence(self, claim_evidence: bytes, file_name: str) -> bool:
        started_at = time.perf_counter()
        try:
            token = self._get_token()
            response = httpx.put(
                f"{self.base_url}/virus_check_file",
                files={
                    "file": (
                        file_name,
                        claim_evidence,
                        "application/octet-stream",
                    )
                },
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            logger.error(
                "SDS claim evidence virus check failed",
                extra=build_log_extra(
                    event="sds_claim_evidence_virus_check_failed",
                    route="sds:virus_check_file",
                    method="PUT",
                    status_code=status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            raise ClaimEvidenceUploadError(
                f"Failed to perform virus check due to a network error: {exc}"
            ) from exc

        if response.status_code == 200:
            logger.info(
                "SDS claim evidence virus check passed",
                extra=build_log_extra(
                    event="sds_claim_evidence_virus_check_passed",
                    route="sds:virus_check_file",
                    method="PUT",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            return True
        elif response.status_code == 400:
            logger.warning(
                "SDS claim evidence virus check failed",
                extra=build_log_extra(
                    event="sds_claim_evidence_virus_check_failed",
                    route="sds:virus_check_file",
                    method="PUT",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            return False
        else:
            logger.error(
                "SDS claim evidence virus check failed",
                extra=build_log_extra(
                    event="sds_claim_evidence_virus_check_failed",
                    route="sds:virus_check_file",
                    method="PUT",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            raise ClaimEvidenceUploadError(
                f"Failed to perform virus check. API status code: {response.status_code}"
            )

    def save_claim_evidence(
        self, claim_evidence: bytes, file_name: str
    ) -> SDSUploadClaimEvidenceResponse:
        unique_file_name, status = self._save_file(
            file_content=claim_evidence,
            file_name=file_name,
            file_kind="claim_evidence",
        )
        return SDSUploadClaimEvidenceResponse(
            sds_file_name=unique_file_name,
            status=status,
        )

    def _save_file(
        self,
        file_content: bytes,
        file_name: str,
        *,
        file_kind: str,
    ) -> tuple[str, str]:
        started_at = time.perf_counter()
        display_name = file_kind.replace("_", " ")
        failed_message = f"SDS {display_name} save failed"
        failed_event = f"sds_{file_kind}_saved_failed"
        success_message = f"SDS {display_name} saved"
        success_event = f"sds_{file_kind}_saved_success"
        path = Path(file_name)
        sanitized_stem = _sanitize_stem(path.stem)
        unique_file_name = f"{sanitized_stem}_{uuid.uuid4()}{path.suffix}"
        token = self._get_token()
        response = httpx.post(
            f"{self.base_url}/save_file",
            files={
                "file": (
                    unique_file_name,
                    file_content,
                    "application/octet-stream",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 201:
            logger.error(
                failed_message,
                extra=build_log_extra(
                    event=failed_event,
                    route="sds:save_file",
                    method="POST",
                    status_code=response.status_code,
                    duration_ms=duration_ms(started_at),
                ),
            )
            return unique_file_name, "FAILURE"

        logger.info(
            success_message,
            extra=build_log_extra(
                event=success_event,
                route="sds:save_file",
                method="POST",
                status_code=response.status_code,
                duration_ms=duration_ms(started_at),
            ),
        )
        return unique_file_name, "SUCCESS"

    def retrieve_coroners_letter(self, file_name: str) -> Iterator[bytes]:
        started_at = time.perf_counter()
        if not file_name or not file_name.strip():
            raise InvalidCoronersLetterDocumentIdError(
                "file_name must be a non-empty string"
            )
        token = self._get_token()
        response = httpx.get(
            f"{self.base_url}/get_file",
            params={"file_key": file_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            message = f"SDS returned {response.status_code} while retrieving coroner's letter for file key {file_name}"
            _raise_sds_retrieval_error(
                message,
                log_message=f"SDS returned {response.status_code} while retrieving coroner's letter",
            )

        try:
            file_url = response.json()["fileURL"]
        except (KeyError, TypeError, ValueError):
            _raise_sds_retrieval_error("Failed to retrieve coroners letter")

        logger.info(
            "SDS coroners letter retrieved",
            extra=build_log_extra(
                event="sds_coroners_letter_retrieved_success",
                route="sds:get_file",
                method="GET",
                status_code=response.status_code,
                duration_ms=duration_ms(started_at),
            ),
        )

        try:
            with httpx.stream("GET", file_url) as stream:
                yield from stream.iter_bytes()
        except (httpx.HTTPError, httpx.StreamError) as exc:
            _raise_sds_retrieval_error(f"Failed to stream coroners letter: \n {exc}")

    def retrieve_claim_evidence(self, file_name: str) -> Iterator[bytes]:
        started_at = time.perf_counter()
        if not file_name or not file_name.strip():
            raise InvalidClaimEvidenceDocumentIdError(
                "file_name must be a non-empty string"
            )
        token = self._get_token()
        response = httpx.get(
            f"{self.base_url}/get_file",
            params={"file_key": file_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            message = f"SDS returned {response.status_code} while retrieving claim evidence for file key {file_name}"
            _raise_sds_claim_evidence_retrieval_error(
                message,
                log_message=f"SDS returned {response.status_code} while retrieving claim evidence",
            )

        try:
            file_url = response.json()["fileURL"]
        except (KeyError, TypeError, ValueError):
            _raise_sds_claim_evidence_retrieval_error(
                "Failed to retrieve claim evidence"
            )

        logger.info(
            "SDS claim evidence retrieved",
            extra=build_log_extra(
                event="sds_claim_evidence_retrieved_success",
                route="sds:get_file",
                method="GET",
                status_code=response.status_code,
                duration_ms=duration_ms(started_at),
            ),
        )

        try:
            with httpx.stream("GET", file_url) as stream:
                yield from stream.iter_bytes()
        except (httpx.HTTPError, httpx.StreamError) as exc:
            _raise_sds_claim_evidence_retrieval_error(
                f"Failed to stream claim evidence: \n {exc}"
            )

    def delete_claim_evidence(self, file_name: str) -> None:
        started_at = time.perf_counter()
        if not file_name or not file_name.strip():
            raise InvalidClaimEvidenceDocumentIdError(
                "file_name must be a non-empty string"
            )
        token = self._get_token()
        response = httpx.delete(
            f"{self.base_url}/delete_files",
            params={"file_keys": [file_name]},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            raise ClaimEvidenceDeleteError(
                f"SDS returned {response.status_code} while deleting claim evidence for file key {file_name}"
            )

        delete_status_code = _extract_delete_status_code(response.json(), file_name)
        if delete_status_code != 204:
            raise ClaimEvidenceDeleteError(
                f"SDS returned {delete_status_code} while deleting claim evidence for file key {file_name}"
            )
        logger.info(
            "SDS claim evidence deleted",
            extra=build_log_extra(
                event="sds_claim_evidence_deleted_success",
                route="sds:delete_files",
                method="DELETE",
                status_code=response.status_code,
                duration_ms=duration_ms(started_at),
            ),
        )

    def delete_coroners_letter(self, file_name: str) -> None:
        started_at = time.perf_counter()
        if not file_name or not file_name.strip():
            raise InvalidCoronersLetterDocumentIdError(
                "file_name must be a non-empty string"
            )
        token = self._get_token()
        response = httpx.delete(
            f"{self.base_url}/delete_files",
            params={"file_keys": [file_name]},
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            raise CoronersLetterDeleteError(
                f"SDS returned {response.status_code} while deleting coroners letter for file key {file_name}"
            )

        delete_status_code = _extract_delete_status_code(response.json(), file_name)
        if delete_status_code != 204:
            raise CoronersLetterDeleteError(
                f"SDS returned {delete_status_code} while deleting coroners letter for file key {file_name}"
            )
        logger.info(
            "SDS coroners letter deleted",
            extra=build_log_extra(
                event="sds_coroners_letter_deleted_success",
                route="sds:delete_files",
                method="DELETE",
                status_code=response.status_code,
                duration_ms=duration_ms(started_at),
            ),
        )


def _sanitize_stem(stem: str) -> str:
    """Replace non-alphanumeric characters (except hyphens and underscores) with underscores."""
    return re.sub(r"[^\w\-]", "_", stem)


def _raise_sds_retrieval_error(
    message_str: str, log_message: str | None = None
) -> None:
    safe_message = log_message or message_str
    logger.error(
        safe_message,
        extra=build_log_extra(
            event="sds_coroners_letter_retrieval_failed",
            route="sds:get_file",
            method="GET",
            error_message=safe_message,
        ),
    )
    raise SDSLetterRetrievalError(message_str)


def _raise_sds_claim_evidence_retrieval_error(
    message_str: str,
    log_message: str | None = None,
) -> None:
    safe_message = log_message or message_str
    logger.error(
        safe_message,
        extra=build_log_extra(
            event="sds_claim_evidence_retrieval_failed",
            route="sds:get_file",
            method="GET",
            error_message=safe_message,
        ),
    )
    raise SDSClaimEvidenceRetrievalError(message_str)


def _extract_delete_status_code(payload, file_name: str) -> int:
    if isinstance(payload, dict):
        direct_match = payload.get(file_name)
        if isinstance(direct_match, int):
            return direct_match
        if isinstance(direct_match, dict):
            status_code = direct_match.get("status_code")
            if isinstance(status_code, int):
                return status_code

        payload_status_code = payload.get("status_code")
        if isinstance(payload_status_code, int):
            return payload_status_code

    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            item_file_name = (
                item.get("file_key") or item.get("filename") or item.get("key")
            )
            status_code = item.get("status_code")
            if item_file_name == file_name and isinstance(status_code, int):
                return status_code

    raise ClaimEvidenceDeleteError(
        f"Unexpected SDS delete response while deleting claim evidence for file key {file_name}"
    )
