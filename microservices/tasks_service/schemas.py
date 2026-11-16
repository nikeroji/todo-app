from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TodoCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: date | None = None


class TodoUpdate(TodoCreate):
    is_completed: bool


class TodoStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_completed: bool


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    is_completed: bool
    created_at: datetime | None
    due_date: date | None
