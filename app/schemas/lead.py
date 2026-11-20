
from pydantic import BaseModel, Field
from typing import Optional


class LeadRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    enquiry: str = Field(min_length=10, max_length=10000)


class LeadProfile(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None

    industry: Optional[str] = None
    requested_service: str
    budget_inr: Optional[float] = None
    timeline: Optional[str] = None

    requirements: list[str] = Field(default_factory=list)
    intent: str
    missing_information: list[str] = Field(default_factory=list)


class LeadAnalysis(LeadProfile):
    priority_score: int
    priority: str
    recommended_action: str
    followup_email: str
    extraction_method: str
