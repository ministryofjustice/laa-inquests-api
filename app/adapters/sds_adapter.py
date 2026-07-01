import logging
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import httpx

from app.models.application.index import SDSUploadCoronersLetterResponse
from app.ports.sds_port import SdsPort
from app.use_cases.exceptions import (
    InvalidCoronersLetterDocumentIdError,
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

    def save_coroners_letter(
        self, coroners_letter: bytes, file_name: str
    ) -> SDSUploadCoronersLetterResponse:
        path = Path(file_name)
        unique_file_name = f"{path.stem}_{uuid.uuid4()}{path.suffix}"
        token = self._get_token()
        response = httpx.post(
            f"{self.base_url}/save_file",
            files={
                "file": (
                    unique_file_name,
                    coroners_letter,
                    "application/octet-stream",
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        if response.status_code != 201:
            return SDSUploadCoronersLetterResponse(
                sds_file_name=unique_file_name,
                status="FAILURE",
            )

        return SDSUploadCoronersLetterResponse(
            sds_file_name=unique_file_name,
            status="SUCCESS",
        )

    def retrieve_coroners_letter(self, file_name: str) -> Iterator[bytes]:
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
            _raise_sds_retrieval_error(message)

        try:
            file_url = response.json()["fileURL"]
        except (KeyError, TypeError, ValueError):
            _raise_sds_retrieval_error("Failed to retrieve coroners letter")

        try:
            with httpx.stream("GET", file_url) as stream:
                yield from stream.iter_bytes()
        except Exception as exc:
            _raise_sds_retrieval_error(f"Failed to stream coroners letter: \n {exc}")


def _raise_sds_retrieval_error(message_str):
    logger.error(message_str)
    raise SDSLetterRetrievalError(message_str)
