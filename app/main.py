import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import desc, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.migrate import migrate_database
from app.agents.lead_graph import run_lead_analysis
from app.database.connection import Base, engine, get_db
from app.database.models import Lead
from app.schemas.lead import LeadRequest
from datetime import datetime, timezone
from app.schemas.lifecycle import (
    LifecycleUpdate,
    AssignmentUpdate,
    ReviewNotesUpdate,
)


logger = logging.getLogger(__name__)

LIFECYCLE_STATUSES = [
    "New",
    "AI Analysed",
    "Under Review",
    "Qualified",
    "Rejected",
    "Follow-up",
    "Converted",
    "Lost",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    migrate_database(engine)
    yield


app = FastAPI(
    title="Cynbit LeadPilot AI",
    description=(
        "AI-assisted lead qualification, explainable prioritization, "
        "service intelligence, and human-reviewed follow-up recommendations."
    ),
    version="1.1.0",
    lifespan=lifespan,
)


def _serialize_result(result: Any) -> dict:
    """Ensure analysis output is a JSON-compatible dictionary."""
    if isinstance(result, dict):
        return result

    # Support Pydantic model results if a service returns one.
    if hasattr(result, "model_dump"):
        value = result.model_dump()
        if isinstance(value, dict):
            return value

    if hasattr(result, "dict"):
        value = result.dict()
        if isinstance(value, dict):
            return value

    raise ValueError("Lead analysis returned an unsupported result format.")


def _load_result_json(raw_value: Any) -> dict:
    """Read historical JSON safely, supporting both dict and JSON string."""
    if isinstance(raw_value, dict):
        return raw_value

    if not raw_value:
        return {}

    try:
        value = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError) as exc:
        logger.exception("A lead record contains invalid result_json.")
        raise HTTPException(
            status_code=500,
            detail="Stored lead analysis is invalid. Please inspect the database record.",
        ) from exc

    if not isinstance(value, dict):
        raise HTTPException(
            status_code=500,
            detail="Stored lead analysis must be a JSON object.",
        )

    return value


def _lead_to_response(lead: Lead) -> dict:
    """Build one consistent API response for list and detail endpoints."""
    result = _load_result_json(lead.result_json)

    # Database fields take precedence over extracted values.
    return {
        **result,
        "id": lead.id,
        "name": lead.name,
        "email": lead.email,
        "company": lead.company,
        "enquiry": lead.enquiry,
        "approval_status": lead.approval_status or "Pending",
        "created_at": (
            lead.created_at.isoformat()
            if getattr(lead, "created_at", None)
            else None
        ),
    }


@app.get("/")
def root():
    return {
        "message": "Welcome to Cynbit LeadPilot AI",
        "version": app.version,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Health check including a lightweight database connectivity check."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "project": "Cynbit LeadPilot AI",
            "version": app.version,
        }
    except SQLAlchemyError as exc:
        logger.exception("Database health check failed.")
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable.",
        ) from exc


@app.post("/api/leads/analyze")
def analyze_customer_lead(
    payload: LeadRequest,
    db: Session = Depends(get_db),
):
    """
    Analyze an enquiry through the LangGraph workflow and persist the result.

    The priority score is an explainable heuristic unless separately trained
    and calibrated using historical conversion outcomes.
    """
    try:
        analysis = run_lead_analysis(
            enquiry=payload.enquiry,
            name=payload.name,
            email=payload.email,
            company=payload.company,
        )
        result = _serialize_result(analysis)

        lead = Lead(
            name=payload.name,
            email=payload.email,
            company=payload.company,
            enquiry=payload.enquiry,
            lifecycle_status="AI Analysed",
            result_json=json.dumps(result, ensure_ascii=False),
        )

        db.add(lead)
        db.commit()
        db.refresh(lead)

        return _lead_to_response(lead)

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Lead analysis or persistence failed.")
        # Keep the response useful for local assessment debugging.
        raise HTTPException(
            status_code=500,
            detail=f"Lead analysis failed: {str(exc)}",
        ) from exc


@app.get("/api/leads")
def get_all_leads(
    db: Session = Depends(get_db),
):
    """Return all saved leads, newest first."""
    try:
        leads = (
            db.query(Lead)
            .order_by(desc(Lead.created_at))
            .all()
        )
        return [_lead_to_response(lead) for lead in leads]

    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        logger.exception("Unable to retrieve leads.")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve leads from the database.",
        ) from exc


@app.get("/api/leads/{lead_id}")
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
):
    """Return the complete analysis for one lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()

    if lead is None:
        raise HTTPException(
            status_code=404,
            detail=f"Lead {lead_id} was not found.",
        )

    return _lead_to_response(lead)



@app.patch("/api/leads/{lead_id}/approval")
def update_approval(
    lead_id: int,
    status: str,
    db: Session = Depends(get_db),
):
    allowed = ["Pending", "Approved", "Rejected"]

    if status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Status must be one of {allowed}",
        )

    lead = db.query(Lead).filter(
        Lead.id == lead_id
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.approval_status = status
    lead.updated_at = datetime.now(timezone.utc)

    if status == "Approved":
        lead.lifecycle_status = "Qualified"
    elif status == "Rejected":
        lead.lifecycle_status = "Rejected"
    else:
        lead.lifecycle_status = "Under Review"

    try:
        db.commit()
        db.refresh(lead)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update approval status.",
        )

    return {
        "id": lead.id,
        "approval_status": lead.approval_status,
        "lifecycle_status": lead.lifecycle_status,
        "message": "Approval status updated",
    }


@app.patch("/api/leads/{lead_id}/lifecycle")
def update_lifecycle(
    lead_id: int,
    payload: LifecycleUpdate,
    db: Session = Depends(get_db),
):
    if payload.status not in LIFECYCLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Invalid lifecycle status",
                "allowed_statuses": LIFECYCLE_STATUSES,
            },
        )

    lead = db.query(Lead).filter(
        Lead.id == lead_id
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Require an explicit human approval before sales progression.
    if payload.status in ["Qualified", "Follow-up", "Converted"]:
        if lead.approval_status != "Approved":
            raise HTTPException(
                status_code=409,
                detail="This lead must be approved before sales progression.",
            )

    if payload.status == "Rejected" and lead.approval_status != "Rejected":
        raise HTTPException(
            status_code=409,
            detail="Reject the lead through human approval before setting this stage.",
        )

    lead.lifecycle_status = payload.status
    lead.updated_at = datetime.now(timezone.utc)

    if payload.status == "Converted" and lead.converted_at is None:
        lead.converted_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(lead)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not update lead lifecycle.",
        )

    return {
        "id": lead.id,
        "lifecycle_status": lead.lifecycle_status,
        "converted_at": (
            lead.converted_at.isoformat()
            if lead.converted_at else None
        ),
        "message": "Lead lifecycle updated successfully",
    }


@app.patch("/api/leads/{lead_id}/assign")
def assign_lead(
    lead_id: int,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(
        Lead.id == lead_id
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.assigned_to = (
        payload.assigned_to.strip()
        if payload.assigned_to and payload.assigned_to.strip()
        else None
    )
    lead.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(lead)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not assign lead.",
        )

    return {
        "id": lead.id,
        "assigned_to": lead.assigned_to,
        "message": "Lead assignment updated",
    }


@app.patch("/api/leads/{lead_id}/notes")
def update_review_notes(
    lead_id: int,
    payload: ReviewNotesUpdate,
    db: Session = Depends(get_db),
):
    lead = db.query(Lead).filter(
        Lead.id == lead_id
    ).first()

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.review_notes = payload.review_notes
    lead.updated_at = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(lead)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not save review notes.",
        )

    return {
        "id": lead.id,
        "review_notes": lead.review_notes,
        "message": "Review notes saved",
    }


@app.get("/api/analytics/summary")
def get_analytics_summary(
    db: Session = Depends(get_db),
):
    leads = db.query(Lead).all()

    lifecycle_counts = {}
    approval_counts = {}
    priority_counts = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
        "Unknown": 0,
    }

    for lead in leads:
        lifecycle = lead.lifecycle_status or "Unknown"
        approval = lead.approval_status or "Unknown"

        lifecycle_counts[lifecycle] = (
            lifecycle_counts.get(lifecycle, 0) + 1
        )
        approval_counts[approval] = (
            approval_counts.get(approval, 0) + 1
        )

        try:
            result = json.loads(lead.result_json or "{}")
            priority = result.get("priority", "Unknown")
        except (TypeError, json.JSONDecodeError):
            priority = "Unknown"

        if priority not in priority_counts:
            priority = "Unknown"

        priority_counts[priority] += 1

    return {
        "total_leads": len(leads),
        "converted_leads": lifecycle_counts.get("Converted", 0),
        "lost_leads": lifecycle_counts.get("Lost", 0),
        "lifecycle_distribution": lifecycle_counts,
        "approval_distribution": approval_counts,
        "priority_distribution": priority_counts,
    }
