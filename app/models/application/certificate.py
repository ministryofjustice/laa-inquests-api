from datetime import date

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApplicationCertificate(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    client_name: str
    client_address: str
    firm_name: str
    office_address: str
    opponent_details: str
    guardian_name: str = "Not applicable"
    guardian_address: str = "Not applicable"

    laa_reference: int
    date_created: date

    certificate_type: str  # Proceeding.certificate_type
    status: str  # ApplicationBase.Status
    effective_date: date  # ApplicationProceeding.certificate_start_date
    end_date: date | None = None
    reinstatement_date: date | None = None  # Will be Not applicable
    cost_limitation: str  # Proceeding.substantive_cost_limitation
    cost_limitation_effective_date: date | None = None
    certificate_limitation: str = "Not applicable"

    care_order_description: str  # Proceeding.proceeding_description
    category_of_law: str  # Proceeding.category_of_law
    current_proceeding_status: str  # ApplicationBase.Status TODO: Confirm. We don't have a field for proceeding status in the ApplicationBase model. Is this the same as the application status?
    date_work_can_commence: date  # ApplicationProceeding.certificate_start_date
    proceeding_end_date: date | None = None
    client_involvement_type: str = "Applicant"
    level_of_service: str  # Proceeding.level_of_service
    date_current_level_of_service_effective: (
        date  # ApplicationProceeding.certificate_start_date
    )
    previous_level_of_service: str = "Not applicable"
    date_previous_level_of_service_effective: str = "Not applicable"
    scope_limitation_heading: str  # Proceeding.scope_limitation_heading
    scope_limitation_description: str  # Proceeding.scope_limitation_description


class ApplicationCertificateResponse(ApplicationCertificate):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
