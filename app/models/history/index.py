from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator
from pydantic import Field as PydanticField
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
    entra_user_object_id: str | None = Field(default=None, nullable=True)
    event_data: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    application_id: int = Field(
        foreign_key="application.application_id", nullable=False
    )

    @property
    def laa_reference(self) -> str:
        """Compatibility alias exposing application_id as a string."""
        return str(self.application_id)


class CreateNoteRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    note_text: str = PydanticField(min_length=1, max_length=10_000)

    @field_validator("note_text")
    @classmethod
    def validate_note_contains_text(cls, note_text: str) -> str:
        if not note_text.strip():
            raise ValueError("Note must contain at least one visible character")
        return note_text


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
