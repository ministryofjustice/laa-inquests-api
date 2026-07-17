import httpx

from app.ports.provider_details_port import ProviderDetailsPort


class ProviderDetailsAdapter(ProviderDetailsPort):
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key

    def get_firm_name(self, firm_code: str) -> str | None:
        try:
            url = f"{self.base_url}/api/v1/provider-firms/{firm_code}"
            response = httpx.get(
                url,
                headers={"X-Authorization": self.api_key},
            )

            response.raise_for_status()
            result = response.json()["firm"]["firmName"]
            return result
        except Exception:
            return None

    def get_office_address(self, office_id: str) -> str | None:
        try:
            url = f"{self.base_url}/api/v1/provider-offices/{office_id}"
            response = httpx.get(
                url,
                headers={"X-Authorization": self.api_key},
            )
            response.raise_for_status()

            full_address = ", ".join(
                filter(
                    None,
                    [
                        response.json()["office"]["addressLine1"],
                        response.json()["office"]["addressLine2"],
                        response.json()["office"]["addressLine3"],
                        response.json()["office"]["addressLine4"],
                        response.json()["office"]["postCode"],
                    ],
                )
            )
            return full_address
        except Exception:
            return None
