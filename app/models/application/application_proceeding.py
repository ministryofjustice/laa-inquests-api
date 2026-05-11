from sqlmodel import Field, SQLModel
from uuid import UUID, uuid4


class ApplicationProceeding(SQLModel, table=True):
    application_proceeding_id: UUID | None = Field(
        default_factory=uuid4, primary_key=True
    )
    application_id: UUID = Field(foreign_key="application.application_id")
    proceeding_id: str = Field(foreign_key="proceeding.proceeding_id")
    client_involvement_type: str | None = "RESPONDENT"
    merits_decision: str | None = "PENDING"
