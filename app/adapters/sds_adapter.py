import uuid
from pathlib import Path

import httpx

from app.models.application.index import SDSUploadCoronersLetterResponse
from app.ports.sds_port import SdsPort


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

    def _get_token(self) -> str:
        response = httpx.post(
            f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": self.scope,
            },
        )
        response.raise_for_status()
        return response.json()["access_token"]

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

    def retrieve_coroners_letter(self, file_name: str) -> bytes:
        token = self._get_token()
        response = httpx.get(
            f"{self.base_url}/get_file",
            params={"file_key": file_name},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.content
