from abc import ABC, abstractmethod


class ReadinessUnavailableError(Exception):
    """A dependency required to serve requests is unavailable."""


class CheckReadinessPort(ABC):
    @abstractmethod
    def check(self) -> None:
        """Check dependencies, raising ReadinessUnavailableError if unavailable."""
        ...
