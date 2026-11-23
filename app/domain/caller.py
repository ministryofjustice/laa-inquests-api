from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCaller:
    office_codes: frozenset[str]


@dataclass(frozen=True)
class CaseworkerCaller:
    pass


Caller = ProviderCaller | CaseworkerCaller
