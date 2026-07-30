import httpx

from app.models.application.index import Address
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

    def get_office_address(self, office_id: str) -> Address | None:
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
            return address
        except Exception:
            return None
