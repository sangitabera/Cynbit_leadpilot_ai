
from typing import Literal

from pydantic import BaseModel, Field


class LeadIntelligence(BaseModel):
    pain_points: list[str] = Field(default_factory=list)

    buying_signals: list[str] = Field(default_factory=list)

    business_requirements: list[str] = Field(default_factory=list)

    recommended_service: str = "Needs clarification"

    service_match_reason: str = ""

    missing_information: list[str] = Field(default_factory=list)

    potential_risks: list[str] = Field(default_factory=list)

    buying_intent: Literal[
        "High",
        "Medium",
        "Low",
        "Unclear"
    ] = "Unclear"

    urgency: Literal[
        "Immediate",
        "Within 1 month",
        "Within 3 months",
        "Flexible",
        "Unknown"
    ] = "Unknown"

    recommended_next_action: str = ""

    reasoning: str = ""
