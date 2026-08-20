from __future__ import annotations

from dataclasses import dataclass

from app.models.application.enums import MeritsDecision


@dataclass(frozen=True)
class ApplicationDomain:
    overall_decision: str

    @property
    def is_granted(self) -> bool:
        return self.overall_decision == MeritsDecision.GRANTED
