import httpx


class ProviderDetailsAdapter:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def get_firm_name(self, firm_code: str) -> str | None:
        try:
            response = httpx.get(f"{self.base_url}/api/v1/provider-firms/{firm_code}")
            response.raise_for_status()
            return response.json()["firm"]["firmName"]
        except Exception:
            return None
