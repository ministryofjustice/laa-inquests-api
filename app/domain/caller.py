from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCaller:
    office_codes: frozenset[str]

    def can_access_resource_owned_by(self, office_id: str) -> bool:
        return office_id in self.office_codes


@dataclass(frozen=True)
class CaseworkerCaller:
    def can_access_resource_owned_by(self, _office_id: str) -> bool:
        return True


Caller = ProviderCaller | CaseworkerCaller
