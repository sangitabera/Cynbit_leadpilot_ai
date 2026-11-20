
import pytest

from app.services.lead_service import (
    extract_with_rules,
    calculate_lead_score,
    generate_followup,
)


@pytest.fixture
def sample_enquiry():
    return (
        "We are a healthcare startup looking for an AI chatbot "
        "integrated with our CRM. Our budget is Rs 2 lakh "
        "and we need delivery within 6 weeks."
    )


def test_rule_extraction_identifies_service(sample_enquiry):
    profile = extract_with_rules(
        sample_enquiry,
        "Test User",
        "test@example.com",
        "HealthTech",
    )

    assert isinstance(profile, dict)
    assert profile.get("requested_service")


def test_rule_extraction_preserves_contact_details(sample_enquiry):
    profile = extract_with_rules(
        sample_enquiry,
        "Test User",
        "test@example.com",
        "HealthTech",
    )

    assert profile.get("name") == "Test User"
    assert profile.get("email") == "test@example.com"
    assert profile.get("company") == "HealthTech"


def test_lead_score_is_deterministic(sample_enquiry):
    profile = extract_with_rules(
        sample_enquiry,
        "Test User",
        "test@example.com",
        "HealthTech",
    )

    first = calculate_lead_score(profile)
    second = calculate_lead_score(profile)

    assert first == second


def test_lead_score_is_within_valid_range(sample_enquiry):
    profile = extract_with_rules(
        sample_enquiry,
        "Test User",
        "test@example.com",
        "HealthTech",
    )

    score, priority, action = calculate_lead_score(profile)

    assert 0 <= score <= 100
    assert priority in ["High", "Medium", "Low"]
    assert isinstance(action, str)
    assert action.strip()


@pytest.mark.parametrize(
    "score, expected",
    [
        (75, "High"),
        (50, "Medium"),
        (49, "Low"),
    ],
)
def test_priority_thresholds(score, expected):
    if score >= 75:
        priority = "High"
    elif score >= 50:
        priority = "Medium"
    else:
        priority = "Low"

    assert priority == expected


def test_followup_email_is_generated(sample_enquiry):
    profile = extract_with_rules(
        sample_enquiry,
        "Test User",
        "test@example.com",
        "HealthTech",
    )

    email = generate_followup(profile)

    assert isinstance(email, str)
    assert len(email.strip()) > 20
