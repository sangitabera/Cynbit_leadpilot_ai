
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app import main


@pytest.fixture
def client(monkeypatch):
    """Create an isolated test database and FastAPI client."""

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )

    monkeypatch.setattr(main, "engine", test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()
    test_engine.dispose()


@pytest.fixture
def mock_analysis(monkeypatch):
    """Replace LangGraph with deterministic test output."""

    def fake_analysis(**kwargs):
        return {
            "requested_service": "AI Chatbot",
            "industry": "Technology",
            "priority_score": 85,
            "priority": "High",
            "recommended_action": "Schedule a discovery call",
            "followup_email": "Hello, let's discuss your requirements.",
            "extraction_method": "rule_based",
            "lead_intelligence": {
                "buying_intent": "High",
                "recommended_service": "AI Automation Suite",
            },
        }

    monkeypatch.setattr(
        main,
        "run_lead_analysis",
        fake_analysis,
    )


def sample_payload():
    return {
        "name": "Test User",
        "email": "test@example.com",
        "company": "Tech Solutions",
        "enquiry": (
            "We need an AI chatbot integrated with our CRM "
            "with a budget of Rs 2 lakh."
        ),
    }


def test_analyze_lead_success(client, mock_analysis):
    response = client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] is not None
    assert data["priority"] == "High"
    assert data["priority_score"] == 85
    assert data["approval_status"] == "Pending"
    assert data["lead_intelligence"]["buying_intent"] == "High"


def test_analyzed_lead_is_persisted(client, mock_analysis):
    created = client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )

    lead_id = created.json()["id"]

    response = client.get("/api/leads")

    assert response.status_code == 200

    leads = response.json()

    assert len(leads) == 1
    assert leads[0]["id"] == lead_id
    assert leads[0]["company"] == "Tech Solutions"
    assert leads[0]["priority"] == "High"


def test_get_lead_by_id(client, mock_analysis):
    created = client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )

    lead_id = created.json()["id"]

    response = client.get(f"/api/leads/{lead_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == lead_id
    assert data["enquiry"] == sample_payload()["enquiry"]
    assert data["email"] == "test@example.com"


def test_get_nonexistent_lead(client):
    response = client.get("/api/leads/99999")

    assert response.status_code == 404


def test_approval_status_can_be_updated(client, mock_analysis):
    created = client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )

    lead_id = created.json()["id"]

    response = client.patch(
        f"/api/leads/{lead_id}/approval",
        params={"status": "Approved"},
    )

    assert response.status_code == 200
    assert response.json()["approval_status"] == "Approved"

    # Verify the updated value was persisted.
    details = client.get(f"/api/leads/{lead_id}")

    assert details.json()["approval_status"] == "Approved"


def test_invalid_approval_status_is_rejected(client, mock_analysis):
    created = client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )

    lead_id = created.json()["id"]

    response = client.patch(
        f"/api/leads/{lead_id}/approval",
        params={"status": "Completed"},
    )

    assert response.status_code == 400


def test_approval_for_nonexistent_lead(client):
    response = client.patch(
        "/api/leads/99999/approval",
        params={"status": "Approved"},
    )

    assert response.status_code == 404



def test_lifecycle_requires_human_approval(client, mock_analysis):
    created = client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )
    lead_id = created.json()["id"]

    response = client.patch(
        f"/api/leads/{lead_id}/lifecycle",
        json={"status": "Converted"},
    )

    assert response.status_code == 409


def test_approved_lead_can_be_converted(client, mock_analysis):
    created = client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )
    lead_id = created.json()["id"]

    approval = client.patch(
        f"/api/leads/{lead_id}/approval",
        params={"status": "Approved"},
    )
    assert approval.status_code == 200

    response = client.patch(
        f"/api/leads/{lead_id}/lifecycle",
        json={"status": "Converted"},
    )

    assert response.status_code == 200
    assert response.json()["lifecycle_status"] == "Converted"
    assert response.json()["converted_at"] is not None


def test_assign_lead(client, mock_analysis):
    created = client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )
    lead_id = created.json()["id"]

    response = client.patch(
        f"/api/leads/{lead_id}/assign",
        json={"assigned_to": "Sales Team"},
    )

    assert response.status_code == 200
    assert response.json()["assigned_to"] == "Sales Team"


def test_update_review_notes(client, mock_analysis):
    created = client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )
    lead_id = created.json()["id"]

    response = client.patch(
        f"/api/leads/{lead_id}/notes",
        json={"review_notes": "Contact customer next Monday."},
    )

    assert response.status_code == 200
    assert response.json()["review_notes"] == (
        "Contact customer next Monday."
    )


def test_analytics_summary(client, mock_analysis):
    client.post(
        "/api/leads/analyze",
        json=sample_payload(),
    )

    response = client.get("/api/analytics/summary")

    assert response.status_code == 200

    data = response.json()

    assert data["total_leads"] == 1
    assert data["lifecycle_distribution"]["AI Analysed"] == 1
    assert data["priority_distribution"]["High"] == 1
