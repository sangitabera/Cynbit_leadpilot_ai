
import logging
from typing import Optional, TypedDict

from langgraph.graph import StateGraph, START, END

from app.config import GROQ_API_KEY
from app.services.lead_service import (
    extract_with_rules,
    extract_with_llm,
    calculate_lead_score,
    generate_followup,
)
from app.services.service_retriever import service_retriever
from app.services.lead_intelligence import lead_intelligence_service


logger = logging.getLogger(__name__)


class LeadState(TypedDict, total=False):
    enquiry: str
    name: Optional[str]
    email: Optional[str]
    company: Optional[str]

    profile: dict
    priority_score: int
    priority: str
    recommended_action: str
    followup_email: str
    extraction_method: str

    service_matches: list[dict]
    lead_intelligence: dict
    intelligence_status: str


# Node 1: Extract customer information
def extract_lead(state: LeadState) -> dict:
    if GROQ_API_KEY:
        try:
            profile = extract_with_llm(
                state["enquiry"],
                state.get("name"),
                state.get("email"),
                state.get("company"),
            )
            method = "groq_llm"

        except Exception:
            logger.exception(
                "LLM extraction failed. Using rule-based fallback."
            )
            profile = extract_with_rules(
                state["enquiry"],
                state.get("name"),
                state.get("email"),
                state.get("company"),
            )
            method = "rule_based_fallback"

    else:
        profile = extract_with_rules(
            state["enquiry"],
            state.get("name"),
            state.get("email"),
            state.get("company"),
        )
        method = "rule_based"

    return {
        "profile": profile,
        "extraction_method": method,
    }


# Node 2: Retrieve relevant Cynbit services
def retrieve_services(state: LeadState) -> dict:
    enquiry = state.get("enquiry", "")

    results = service_retriever.search(
        enquiry,
        top_k=3,
    )

    return {
        "service_matches": results,
    }


# Node 3: Generate structured lead intelligence
def analyze_lead_intelligence(state: LeadState) -> dict:
    enquiry = state.get("enquiry", "")

    try:
        intelligence = lead_intelligence_service.analyze(
            enquiry,
            relevant_services=state.get("service_matches", []),
        )

        return {
            "lead_intelligence": intelligence,
            "intelligence_status": "completed",
        }

    except Exception:
        logger.exception("Lead intelligence node failed")

        return {
            "lead_intelligence": {},
            "intelligence_status": "failed",
        }


# Node 4: Calculate lead priority
def score_lead(state: LeadState) -> dict:
    score, priority, action = calculate_lead_score(
        state["profile"]
    )

    return {
        "priority_score": score,
        "priority": priority,
        "recommended_action": action,
    }


# Node 5: Generate personalized follow-up
def generate_followup_node(state: LeadState) -> dict:
    email = generate_followup(state["profile"])

    return {
        "followup_email": email,
    }


# Node 6: Combine all results
def finalize_lead(state: LeadState) -> dict:
    result = state["profile"].copy()

    result.update({
        "priority_score": state["priority_score"],
        "priority": state["priority"],
        "recommended_action": state["recommended_action"],
        "followup_email": state["followup_email"],
        "extraction_method": state["extraction_method"],
        "service_matches": state.get("service_matches", []),
        "lead_intelligence": state.get("lead_intelligence", {}),
        "intelligence_status": state.get(
            "intelligence_status",
            "unavailable",
        ),
    })

    return {
        "profile": result,
    }


# Build the LangGraph workflow
def build_lead_graph():
    workflow = StateGraph(LeadState)

    workflow.add_node("extract_lead", extract_lead)
    workflow.add_node("retrieve_services", retrieve_services)
    workflow.add_node(
        "analyze_lead_intelligence",
        analyze_lead_intelligence,
    )
    workflow.add_node("score_lead", score_lead)
    workflow.add_node(
        "generate_followup",
        generate_followup_node,
    )
    workflow.add_node("finalize", finalize_lead)

    workflow.add_edge(START, "extract_lead")

    workflow.add_edge(
        "extract_lead",
        "retrieve_services",
    )

    workflow.add_edge(
        "retrieve_services",
        "analyze_lead_intelligence",
    )

    workflow.add_edge(
        "analyze_lead_intelligence",
        "score_lead",
    )

    workflow.add_edge(
        "score_lead",
        "generate_followup",
    )

    workflow.add_edge(
        "generate_followup",
        "finalize",
    )

    workflow.add_edge("finalize", END)

    return workflow.compile()


lead_graph = build_lead_graph()


def run_lead_analysis(
    enquiry: str,
    name=None,
    email=None,
    company=None,
):
    result = lead_graph.invoke({
        "enquiry": enquiry,
        "name": name,
        "email": email,
        "company": company,
    })

    return result["profile"]
