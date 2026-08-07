from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.history.enums import ActorType


class HistoryEvent(SQLModel, table=True):
    __tablename__ = "history_event"

    id: int | None = Field(default=None, primary_key=True)
    event_reference: str = Field(nullable=False)
    timestamp: datetime = Field(
        nullable=False, default_factory=lambda: datetime.now(UTC)
    )
    actor: str = Field(nullable=False)
    actor_type: ActorType = Field(nullable=False)
    event_description: str = Field(nullable=False)
    event_data: str | None = Field(default=None, nullable=True)
    laa_reference: int = Field(foreign_key="application.laa_reference", nullable=False)
