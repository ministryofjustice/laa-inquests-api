import enum
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import Column
from sqlmodel import Field, Relationship, SQLModel, Enum
from datetime import datetime, UTC


class ProceedingId(str, enum.Enum):
    PC049 = "PC049"
    TEST1 = "TEST1"


class ApplicationBase(SQLModel):
    laa_reference: int | None = Field(default_factory=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
    status: str | None = "LIVE"
    used_delegated_functions: bool = True
    application_type: str | None = "INITIAL"
    auto_grant: bool | None = True
    overall_decision: str | None = "PENDING"


class Application(ApplicationBase, table=True):
    proceedings: list["ApplicationProceeding"] = Relationship(
        back_populates="application"
    )


class ApplicationProceeding(SQLModel, table=True):
    proceeding_id: ProceedingId = Field(sa_column=Column(Enum(ProceedingId)))
    application_proceeding_id: int | None = Field(default=None, primary_key=True)
    proceeding_description: str | None = "This is the proceeding description"
    category_of_law: str | None = "INQUESTS"
    certificate_type: str | None = "SUBSTANTIVE"
    level_of_service: str | None = "FULL_REPRESENTATION"
    matter_type: str | None = "INQUESTS"
    scope_limitation_heading: str | None = "FINAL_HEARING"
    scope_description: str | None = "This is the scope description"
    substantive_cost_limitation: int | None = 25000
    client_involvement_type: str | None = "RESPONDENT"
    merits_decision: str | None = "PENDING"
    laa_reference: int = Field(foreign_key="application.laa_reference")
    application: Application = Relationship(back_populates="proceedings")


class ProceedingCreate(BaseModel):
    proceeding_id: str


class ApplicationCreate(BaseModel):
    # documents: list[Document]
    # provider: Provider
    # client: Client
    proceedings: list[ProceedingCreate]


class ProceedingResponse(BaseModel):
    proceeding_id: str
    proceeding_description: Optional[str] = None
    category_of_law: str
    certificate_type: str
    level_of_service: str
    matter_type: str
    scope_limitation_heading: str
    scope_description: str
    substantive_cost_limitation: int
    client_involvement_type: str
    merits_decision: str

    class Config:
        orm_mode = True


class ApplicationResponse(BaseModel):
    laa_reference: int
    created_at: datetime
    updated_at: datetime
    status: str
    used_delegated_functions: bool
    application_type: str
    auto_grant: bool
    overall_decision: str
    proceedings: list[ProceedingResponse] = []

    class Config:
        orm_mode = True
