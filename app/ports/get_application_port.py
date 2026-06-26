from typing import Protocol

from app.ports.application_lookup_port import ApplicationLookupPort


class GetApplicationPort(ApplicationLookupPort, Protocol):
    pass
