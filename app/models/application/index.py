from pydantic import BaseModel
from sqlmodel import Field, SQLModel
from datetime import datetime, UTC
from uuid import UUID, uuid4


class Application(SQLModel, table=True):
    application_id: UUID | None = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column_kwargs={"onupdate": lambda: datetime.now(UTC)},
    )
    status: str | None = "PENDING"
    laa_reference: str
    used_delegated_functions: bool | None = True
    application_type: str | None = "INITIAL"
    auto_grant: bool | None = True
    overall_decision: str | None = "PENDING"


class ApplicationRequest(BaseModel):
    # status: str
    laa_reference: str
    # used_delegated_functions: bool
    # application_type: str
    # auto_grant: bool
    # overall_decision: str
    # documents: list[Document]
    # provider: Provider
    # client: Client
    # proceedings: list[Proceeding]
    # notes: list[ApplicationNote]
    # opponents: list[Opponent]
