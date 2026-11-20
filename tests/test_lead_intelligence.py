
from unittest.mock import patch

import pytest

from app.services.lead_intelligence import LeadIntelligenceService


def test_empty_enquiry_is_rejected():
    service = LeadIntelligenceService()

    with pytest.raises(ValueError):
        service.analyze("   ")


def test_fallback_returns_valid_structure():
    service = LeadIntelligenceService()

    with patch.object(service, "client", None):
        result = service.analyze(
            "We need an AI voice agent for customer support."
        )

    assert result["buying_intent"] == "Unclear"
    assert result["recommended_service"] == "AI Automation Suite"
    assert result["missing_information"]
    assert result["recommended_next_action"]


def test_fallback_does_not_claim_conversion_probability():
    service = LeadIntelligenceService()

    with patch.object(service, "client", None):
        result = service.analyze(
            "We are exploring software development."
        )

    assert "conversion_probability" not in result
    assert result["buying_intent"] == "Unclear"


def test_fallback_handles_unrelated_enquiry():
    service = LeadIntelligenceService()

    with patch.object(service, "client", None):
        result = service.analyze(
            "I want information about gardening."
        )

    assert result["recommended_service"] == "Needs clarification"
    assert result["buying_intent"] == "Unclear"
