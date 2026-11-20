import pytest
from app.services.service_retriever import ServiceRetriever

@pytest.fixture
def retriever():
    return ServiceRetriever()

def test_retrieves_ai_automation_service(retriever):
    results = retriever.search(
        "We need an AI voice agent to automate customer support."
    )

    assert results
    assert results[0]["service_id"] == "ai_automation_suite"

def test_retrieves_cynbit_studio(retriever):
    results = retriever.search(
        "We need coding assessments to evaluate developers."
    )

    assert results
    assert results[0]["service_id"] == "cynbit_studio"

def test_returns_empty_for_blank_query(retriever):
    assert retriever.search("   ") == []

def test_respects_top_k(retriever):
    results = retriever.search(
        "We need software development and automation.",
        top_k=2,
    )

    assert len(results) <= 2

def test_rejects_invalid_top_k(retriever):
    with pytest.raises(ValueError):
        retriever.search("AI automation", top_k=0)