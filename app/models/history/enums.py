from enum import StrEnum


class ActorType(StrEnum):
    SYSTEM = "System"
    CASEWORKER = "Caseworker"
    PROVIDER = "Provider"


class EventReference(StrEnum):
    APPLICATION_SUBMITTED = "EVT-BUS-APP-001"
    APPLICAION_ASSESSMENT_COMPLETED = "EVT-BUS-APP-002"
