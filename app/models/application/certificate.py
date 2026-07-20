from datetime import date

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.application.index import Address


class ApplicationCertificate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    client_name: str
    client_address: Address | None
    firm_name: str
    office_address: str
    opponent_details: str
    guardian_name: str = "Not applicable"
    guardian_address: str = "Not applicable"

    laa_reference: int
    date_created: date

    certificate_type: str
    status: str
    effective_date: date
    end_date: date | None = None
    reinstatement_date: date | None = None
    cost_limitation: int
    cost_limitation_effective_date: date | None = None
    certificate_limitation: str = "Not applicable"

    care_order_description: str
    category_of_law: str
    current_proceeding_status: str
    date_work_can_commence: date
    proceeding_end_date: date | None = None
    client_involvement_type: str = "Applicant"
    level_of_service: str
    date_current_level_of_service_effective: (
        date  # ApplicationProceeding.certificate_start_date
    )
    previous_level_of_service: str = "Not applicable"
    date_previous_level_of_service_effective: str = "Not applicable"
    scope_limitation_heading: str
    scope_limitation_description: str


class ApplicationCertificateResponse(ApplicationCertificate):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
