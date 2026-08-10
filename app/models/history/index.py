from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sqlmodel import Field, SQLModel

from app.models.history.enums import ActorType, EventReference


class HistoryEvent(SQLModel, table=True):
    __tablename__ = "history_event"

    id: int | None = Field(default=None, primary_key=True)
    event_reference: EventReference = Field(nullable=False)
    timestamp: datetime = Field(
        nullable=False, default_factory=lambda: datetime.now(UTC)
    )
    actor: str = Field(nullable=False)
    actor_type: ActorType = Field(nullable=False)
    event_description: str = Field(nullable=False)
    event_data: str | None = Field(default=None, nullable=True)
    laa_reference: int = Field(foreign_key="application.laa_reference", nullable=False)


class HistoryEventResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    timestamp: datetime
    actor: str
    event_description: str
    event_data: str | None
