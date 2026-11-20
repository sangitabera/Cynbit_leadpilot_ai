
from typing import Optional

from pydantic import BaseModel, Field


class LifecycleUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)


class AssignmentUpdate(BaseModel):
    assigned_to: Optional[str] = Field(
        default=None,
        max_length=200,
    )


class ReviewNotesUpdate(BaseModel):
    review_notes: Optional[str] = Field(
        default=None,
        max_length=5000,
    )
