from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer
from pydantic.alias_generators import to_camel
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.history.enums import ActorType, HistoryEventReference


class HistoryEvent(SQLModel, table=True):
    __tablename__ = "history_event"

    id: int | None = Field(default=None, primary_key=True)
    event_reference: HistoryEventReference = Field(nullable=False)
    timestamp: datetime = Field(
        nullable=False, default_factory=lambda: datetime.now(UTC)
    )
    actor: str = Field(nullable=False)
    actor_type: ActorType = Field(nullable=False)
    event_data: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    laa_reference: int = Field(foreign_key="application.laa_reference", nullable=False)


class HistoryEventResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )
    timestamp: datetime
    actor: str
    event_reference: HistoryEventReference
    event_data: dict | None

    @field_serializer("event_data", when_used="json")
    def serialize_event_data(self, event_data: dict | None) -> dict | None:
        if event_data is None:
            return None
        return _camelize_json_keys(event_data)


def _camelize_json_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            to_camel(str(key)): _camelize_json_keys(item) for key, item in value.items()
        }
    if isinstance(value, list):
        return [_camelize_json_keys(item) for item in value]
    return value
