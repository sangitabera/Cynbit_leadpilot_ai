"""Cynbit LeadPilot AI - Streamlit frontend.

Run from the repository root:
    streamlit run frontend/streamlit_app.py
"""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st

from frontend.components.analytics import render_analytics
from frontend.components.lead_intelligence import render_lead_intelligence
from frontend.components.pipeline import render_pipeline
from frontend.components.executive_analytics import (
    render_executive_analytics,
)
from frontend.components.evaluation_dashboard import (
    render_evaluation_dashboard,
)

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

API_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT = int(os.getenv("API_TIMEOUT", "20"))
ANALYSIS_TIMEOUT = int(os.getenv("ANALYSIS_TIMEOUT", "90"))

st.set_page_config(
    page_title="Cynbit LeadPilot AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# -----------------------------------------------------------------------------
# Styling - uses Streamlit theme variables for light/dark compatibility
# -----------------------------------------------------------------------------

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background: var(--background-color);
            color: var(--text-color);
        }

        [data-testid="stSidebar"] {
            background: #073f40;
        }
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--text-color) !important;
        }

        .hero {
            background: linear-gradient(120deg, #075e60, #087f80);
            color: #ffffff !important;
            padding: 26px 30px;
            border-radius: 16px;
            margin-bottom: 22px;
        }
        .hero h1 {
            color: #ffffff !important;
            font-size: 30px;
            font-weight: 800;
            margin: 0 0 8px 0;
        }
        .hero p {
            color: #e0f2f1 !important;
            font-size: 14px;
            margin: 0;
        }

        .section-title {
            font-size: 21px;
            font-weight: 700;
            color: var(--text-color) !important;
            margin: 12px 0;
        }

        div[data-testid="stMetric"] {
            background: var(--secondary-background-color);
            border: 1px solid var(--border-color);
            padding: 15px;
            border-radius: 12px;
        }
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {
            color: var(--text-color) !important;
        }

        div[data-testid="stForm"] {
            background: var(--secondary-background-color);
            padding: 18px;
            border-radius: 14px;
            border: 1px solid var(--border-color);
        }

        input, textarea {
            color: var(--text-color) !important;
        }

        [data-testid="stCaptionContainer"] {
            color: var(--text-color);
            opacity: 0.78;
        }

        .stButton button[kind="primary"],
        .stFormSubmitButton button {
            background: #087879;
            border: none;
            color: #ffffff !important;
            border-radius: 8px;
        }

        [data-testid="stDataFrame"] {
            border-radius: 10px;
        }

        hr {
            border-color: var(--border-color);
        }

        [data-testid="stAlert"] {
            border-radius: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# API helpers
# -----------------------------------------------------------------------------

def _api_url(endpoint: str) -> str:
    return f"{API_URL}/{endpoint.lstrip('/')}"


def api_get(endpoint: str) -> Any:
    response = requests.get(_api_url(endpoint), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def api_post(endpoint: str, payload: dict[str, Any], timeout: int = ANALYSIS_TIMEOUT) -> Any:
    response = requests.post(
        _api_url(endpoint),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def api_patch(endpoint: str, params: dict[str, Any]) -> Any:
    """PATCH using query parameters to match the existing approval API."""
    response = requests.patch(
        _api_url(endpoint),
        params=params,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def extract_lead_list(payload: Any) -> list[dict[str, Any]]:
    """Accept either a direct list or common paginated/list response shapes."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if isinstance(payload, dict):
        for key in ("leads", "items", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

    return []


def get_leads(show_error: bool = True) -> list[dict[str, Any]]:
    try:
        return extract_lead_list(api_get("/api/leads"))
    except requests.RequestException as exc:
        if show_error:
            st.error(f"Unable to retrieve leads from the API: {exc}")
        return []
    except (ValueError, TypeError) as exc:
        if show_error:
            st.error(f"The API returned invalid lead data: {exc}")
        return []


def safe_value(value: Any) -> str | None:
    """Convert CSV values to clean strings without emitting 'nan'."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    cleaned = str(value).strip()
    return cleaned or None


def normalize_analysis_result(payload: Any) -> dict[str, Any]:
    """Normalize common API response shapes while preserving database fields."""
    if not isinstance(payload, dict):
        raise ValueError("The analysis endpoint did not return a JSON object.")

    result = dict(payload)
    nested = result.get("profile")

    if isinstance(nested, dict):
        # Keep top-level metadata (e.g. database id) and expose profile fields.
        result = {**nested, **result}

    nested_result = result.get("result_json")
    if isinstance(nested_result, str):
        try:
            import json
            decoded = json.loads(nested_result)
            if isinstance(decoded, dict):
                result = {**decoded, **result}
        except json.JSONDecodeError:
            pass
    elif isinstance(nested_result, dict):
        result = {**nested_result, **result}

    return result


def show_api_error(prefix: str, exc: requests.RequestException) -> None:
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        st.error(f"{prefix}: {detail}")
    else:
        st.error(f"{prefix}: {exc}")


# -----------------------------------------------------------------------------
# Sidebar and page header
# -----------------------------------------------------------------------------

with st.sidebar:
    st.markdown("# 🎯 LeadPilot AI")
    st.caption("Cynbit Intelligence Suite")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Overview",
            "Analyze Lead",
            "Lead Pipeline",
            "Sales Pipeline",
            "Analytics",
            "Executive Analytics",
            "Bulk Analysis",
            "About Project",
            "AI Evaluation",
        ],
        key="navigation_page",
    )

    st.divider()
    st.caption("AI-assisted business intelligence")
    st.caption("Assessment prototype · v1.0.0")

st.markdown(
    """
    <div class="hero">
        <h1>Cynbit LeadPilot AI 🚀</h1>
        <p>Intelligent lead qualification, explainable prioritization and AI-assisted sales workflows.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# Fetch once per Streamlit rerun. Refresh button is provided on data pages.
leads = get_leads()


# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------

if page == "Overview":
    st.markdown('<div class="section-title">Business Overview</div>', unsafe_allow_html=True)

    total = len(leads)
    high = sum(lead.get("priority") == "High" for lead in leads)
    medium = sum(lead.get("priority") == "Medium" for lead in leads)
    low = sum(lead.get("priority") == "Low" for lead in leads)
    approved = sum(lead.get("approval_status") == "Approved" for lead in leads)
    pending = sum(lead.get("approval_status", "Pending") == "Pending" for lead in leads)
    rejected = sum(lead.get("approval_status") == "Rejected" for lead in leads)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Leads", total)
    col2.metric("High Priority", high)
    col3.metric("Approved", approved)
    col4.metric("Pending Review", pending)

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Lead Priority Distribution")
        if total:
            priority_df = pd.DataFrame(
                {"Priority": ["High", "Medium", "Low"], "Count": [high, medium, low]}
            )
            st.bar_chart(priority_df.set_index("Priority"))
        else:
            st.info("No lead data available yet. Analyze a lead to populate this dashboard.")

    with right:
        st.subheader("Human Review Distribution")
        if total:
            approval_df = pd.DataFrame(
                {
                    "Status": ["Approved", "Pending", "Rejected"],
                    "Count": [approved, pending, rejected],
                }
            )
            st.bar_chart(approval_df.set_index("Status"))
        else:
            st.info("Approval insights will appear after leads are submitted.")

    st.divider()
    st.subheader("Recent Leads")
    if leads:
        recent_df = pd.DataFrame(leads)
        columns = [
            "id", "name", "company", "requested_service", "priority_score",
            "priority", "approval_status",
        ]
        available = [column for column in columns if column in recent_df.columns]
        st.dataframe(
            recent_df[available].head(10),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Your lead pipeline is currently empty.")

    st.caption(
        "Priority is a rule-based/LLM-assisted assessment signal, not a calibrated probability of conversion."
    )


# -----------------------------------------------------------------------------
# Analyze one lead
# -----------------------------------------------------------------------------

elif page == "Analyze Lead":
    st.subheader("AI Lead Analysis")
    st.write(
        "Submit a customer enquiry to extract business needs, assess lead priority, "
        "retrieve relevant Cynbit services and prepare a follow-up draft."
    )

    with st.form("lead_analysis_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Contact Name", placeholder="e.g. Aditi Sharma")
            company = st.text_input("Company Name", placeholder="e.g. Acme Technologies")
        with col2:
            email = st.text_input("Email Address", placeholder="name@company.com")

        enquiry = st.text_area(
            "Customer Enquiry",
            height=180,
            placeholder=(
                "We are a technology startup looking to build an AI-powered chatbot "
                "integrated with our CRM. Our budget is Rs 2 lakh and we want to "
                "launch within 6 weeks."
            ),
        )

        submitted = st.form_submit_button(
            "🚀 Analyze Lead",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if len(enquiry.strip()) < 10:
            st.warning("Please enter a customer enquiry containing at least 10 characters.")
        else:
            payload = {
                "name": name.strip() or None,
                "email": email.strip() or None,
                "company": company.strip() or None,
                "enquiry": enquiry.strip(),
            }

            try:
                with st.spinner("AI agents are analyzing your lead..."):
                    raw_result = api_post("/api/leads/analyze", payload)
                    result = normalize_analysis_result(raw_result)

                st.session_state["latest_lead_analysis"] = result
                st.session_state["analysis_result"] = result
                st.success("Lead analysis completed successfully!")

                # The component receives the complete normalized response.
                render_lead_intelligence(result)

            except requests.RequestException as exc:
                show_api_error("Analysis request failed", exc)
            except (ValueError, TypeError) as exc:
                st.error(f"Could not interpret the analysis response: {exc}")
            except Exception as exc:
                st.error(f"Unexpected analysis error: {exc}")

    result = st.session_state.get("analysis_result")
    if isinstance(result, dict):
        st.divider()
        lead_id = result.get("id", "Not saved")
        st.subheader(f"Latest Analysis — Lead #{lead_id}")

        score = result.get("priority_score", "—")
        priority = result.get("priority", "Unclassified")
        method = result.get("extraction_method", "Not provided")

        a, b, c = st.columns(3)
        a.metric("Priority Score", f"{score}/100" if score != "—" else "—")
        b.metric("Priority", priority)
        c.metric("Extraction Method", str(method).replace("_", " ").title())

        left, right = st.columns(2)
        with left:
            st.markdown("### Extracted Profile")
            profile_fields = {
                "Industry": result.get("industry"),
                "Requested Service": result.get("requested_service"),
                "Budget (INR)": result.get("budget_inr"),
                "Timeline": result.get("timeline"),
                "Intent": result.get("intent"),
                "Requirements": result.get("requirements"),
                "Missing Information": result.get("missing_information"),
            }
            st.json(profile_fields)

        with right:
            st.markdown("### Recommended Action")
            st.info(result.get("recommended_action") or "No recommendation was returned.")

            followup = result.get("followup_email") or ""
            st.markdown("### Follow-up Email Draft")
            st.text_area(
                "Review and edit the generated message",
                value=followup,
                height=240,
                key=f"email_draft_{lead_id}",
            )
            if followup:
                st.download_button(
                    "📥 Download Follow-up Draft",
                    data=followup,
                    file_name=f"lead_{lead_id}_followup.txt",
                    mime="text/plain",
                )

        st.caption(
            "Human review is required before acting on AI recommendations. "
            "The priority score is an illustrative heuristic, not a calibrated conversion probability."
        )


# -----------------------------------------------------------------------------
# Lead pipeline and human review
# -----------------------------------------------------------------------------

elif page == "Lead Pipeline":
    st.subheader("Lead Management Pipeline")

    refresh_col, _ = st.columns([1, 5])
    with refresh_col:
        if st.button("↻ Refresh leads"):
            st.rerun()

    if not leads:
        st.info("No leads found. Analyze a lead first.")
    else:
        filter1, filter2, filter3 = st.columns(3)
        with filter1:
            priority_filter = st.selectbox("Priority", ["All", "High", "Medium", "Low"])
        with filter2:
            approval_filter = st.selectbox(
                "Approval", ["All", "Pending", "Approved", "Rejected"]
            )
        with filter3:
            search_text = st.text_input("Search name / company / service").strip().lower()

        filtered = []
        for lead in leads:
            if priority_filter != "All" and lead.get("priority") != priority_filter:
                continue
            if approval_filter != "All" and lead.get("approval_status", "Pending") != approval_filter:
                continue
            searchable = " ".join(
                str(lead.get(field) or "")
                for field in ("name", "company", "requested_service", "enquiry")
            ).lower()
            if search_text and search_text not in searchable:
                continue
            filtered.append(lead)

        st.caption(f"Showing {len(filtered)} of {len(leads)} leads")
        if not filtered:
            st.info("No leads match the selected filters.")
        else:
            pipeline_df = pd.DataFrame(filtered)
            display_columns = [
                "id", "name", "company", "requested_service", "priority_score",
                "priority", "approval_status",
            ]
            available_columns = [c for c in display_columns if c in pipeline_df.columns]
            st.dataframe(
                pipeline_df[available_columns],
                use_container_width=True,
                hide_index=True,
            )

            st.divider()
            st.markdown("### Human Review")
            lead_ids = [lead.get("id") for lead in filtered if lead.get("id") is not None]
            if not lead_ids:
                st.warning("The API response does not include lead IDs, so review cannot be updated.")
            else:
                selected_id = st.selectbox("Select Lead ID", lead_ids)
                selected_lead = next(
                    lead for lead in filtered if lead.get("id") == selected_id
                )

                detail_left, detail_right = st.columns(2)
                with detail_left:
                    st.write(f"**Contact:** {selected_lead.get('name') or 'N/A'}")
                    st.write(f"**Company:** {selected_lead.get('company') or 'N/A'}")
                    st.write(f"**Service:** {selected_lead.get('requested_service') or 'N/A'}")
                    st.write(f"**Priority:** {selected_lead.get('priority', 'N/A')}")
                    st.write(f"**Score:** {selected_lead.get('priority_score', 'N/A')}")
                with detail_right:
                    st.write("**Recommended action:**")
                    st.info(selected_lead.get("recommended_action") or "Not available")

                with st.expander("View original enquiry"):
                    st.write(selected_lead.get("enquiry") or "Not available")

                statuses = ["Pending", "Approved", "Rejected"]
                current_status = selected_lead.get("approval_status", "Pending")
                if current_status not in statuses:
                    current_status = "Pending"

                new_status = st.selectbox(
                    "Human decision",
                    statuses,
                    index=statuses.index(current_status),
                    key=f"approval_status_{selected_id}",
                )

                if st.button("Save Review Decision", type="primary"):
                    try:
                        api_patch(
                            f"/api/leads/{selected_id}/approval",
                            {"status": new_status},
                        )
                        st.success("Review decision saved.")
                        st.rerun()
                    except requests.RequestException as exc:
                        show_api_error("Could not update approval", exc)


# -----------------------------------------------------------------------------
# Sales Pipeline
# -----------------------------------------------------------------------------

elif page == "Sales Pipeline":
    try:
        leads = api_get("/api/leads")

        if isinstance(leads, list):
            render_pipeline(leads, API_URL)
        else:
            st.error("Invalid API response.")

    except requests.RequestException as exc:
        st.error(f"Could not load pipeline: {exc}")

# -----------------------------------------------------------------------------
# Analytics
# -----------------------------------------------------------------------------

elif page == "Analytics":
    st.subheader("Lead Intelligence Analytics")
    st.caption("Explore lead quality, service demand and review status from saved records.")

    if st.button("↻ Refresh analytics"):
        st.rerun()

    if leads:
        render_analytics(leads)
    else:
        st.info("No saved leads are available for analytics yet.")

# -----------------------------------------------------------------------------
# Executive Analytics
# -----------------------------------------------------------------------------

elif page == "Executive Analytics":
    try:
        summary = api_get("/api/analytics/summary")

        render_executive_analytics(summary)

    except requests.RequestException as exc:
        st.error(f"Could not load analytics: {exc}")


# -----------------------------------------------------------------------------
# Bulk analysis
# -----------------------------------------------------------------------------

elif page == "Bulk Analysis":
    st.subheader("Bulk Lead Intelligence")
    st.write(
        "Upload a CSV file to submit multiple customer enquiries through the same lead-analysis workflow."
    )
    st.caption("Required column: enquiry. Optional columns: name, email, company.")

    uploaded = st.file_uploader("Upload customer leads CSV", type=["csv"])

    if uploaded is not None:
        try:
            csv_df = pd.read_csv(uploaded)
            if "enquiry" not in csv_df.columns:
                st.error("CSV must contain a column named 'enquiry'.")
            elif csv_df.empty:
                st.warning("The uploaded CSV contains no records.")
            else:
                st.write("### Uploaded Dataset Preview")
                st.dataframe(csv_df.head(10), use_container_width=True, hide_index=True)
                st.caption(f"{len(csv_df)} rows detected")

                if st.button("🚀 Analyze All Leads", type="primary"):
                    results: list[dict[str, Any]] = []
                    progress = st.progress(0.0)
                    status = st.empty()

                    for position, (_, row) in enumerate(csv_df.iterrows(), start=1):
                        enquiry_value = safe_value(row.get("enquiry"))
                        payload = {
                            "name": safe_value(row.get("name")),
                            "email": safe_value(row.get("email")),
                            "company": safe_value(row.get("company")),
                            "enquiry": enquiry_value or "",
                        }

                        if len(payload["enquiry"]) < 10:
                            results.append(
                                {"row": position, "error": "Enquiry must contain at least 10 characters."}
                            )
                        else:
                            try:
                                output = api_post(
                                    "/api/leads/analyze",
                                    payload,
                                    timeout=ANALYSIS_TIMEOUT,
                                )
                                normalized = normalize_analysis_result(output)
                                normalized["source_row"] = position
                                results.append(normalized)
                            except requests.RequestException as exc:
                                results.append({"row": position, "error": str(exc)})
                            except (ValueError, TypeError) as exc:
                                results.append({"row": position, "error": str(exc)})

                        progress.progress(position / len(csv_df))
                        status.caption(f"Processed {position} of {len(csv_df)} rows")

                    st.session_state["bulk_results"] = results
                    success_count = sum("error" not in item for item in results)
                    error_count = len(results) - success_count
                    st.success(f"Completed: {success_count} successful, {error_count} failed.")

        except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
            st.error(f"Unable to read CSV: {exc}")

    bulk_results = st.session_state.get("bulk_results", [])
    if bulk_results:
        st.divider()
        st.subheader("Bulk Analysis Results")
        result_df = pd.DataFrame(bulk_results)
        st.dataframe(result_df, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Download Analysis Results",
            data=result_df.to_csv(index=False).encode("utf-8"),
            file_name="cynbit_lead_analysis.csv",
            mime="text/csv",
        )


# -----------------------------------------------------------------------------
# About
# -----------------------------------------------------------------------------

elif page == "About Project":
    st.subheader("About Cynbit LeadPilot AI")
    st.write(
        "Cynbit LeadPilot AI is an AI-assisted lead intelligence proof of concept. "
        "It demonstrates how customer enquiries can be transformed into structured "
        "lead profiles, explainable priority recommendations and human-reviewed sales workflows."
    )

    st.markdown("### Core Technologies")
    technologies = {
        "Backend API": "FastAPI",
        "Frontend": "Streamlit",
        "Agent Orchestration": "LangGraph",
        "LLM Provider": "Groq API (optional; rule-based fallback available)",
        "Database": "SQLite / PostgreSQL (depending on configuration)",
        "Validation": "Pydantic",
        "Data Processing": "Pandas",
        "Analytics": "Plotly / Streamlit charts",
    }
    st.table(pd.DataFrame(list(technologies.items()), columns=["Component", "Technology"]))

    st.markdown("### AI Capabilities")
    st.markdown(
        """
        - Customer enquiry understanding and structured extraction
        - Service relevance retrieval
        - Lead priority scoring with visible rationale/recommendations
        - Buying-intent and business-need analysis (when enabled by backend)
        - Personalized follow-up email drafting
        - Human-in-the-loop approval workflow
        - CSV-based bulk lead analysis
        - Pipeline and lead-demand analytics
        """
    )

    st.warning(
        "Assessment prototype: the priority score is heuristic/AI-assisted and has not been "
        "trained or calibrated against Cynbit's historical lead-conversion data. "
        "AI-generated recommendations and follow-up drafts require human review."
    )

# -----------------------------------------------------------------------------
# AI Evaluation
# -----------------------------------------------------------------------------

elif page == "AI Evaluation":
    render_evaluation_dashboard()


# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------

st.divider()
st.markdown(
    """
    <div style="text-align:center;color:#718585;font-size:12px;">
        Cynbit LeadPilot AI · AI-Assisted Lead Intelligence<br>
        Assessment Proof of Concept · 2026
    </div>
    """,
    unsafe_allow_html=True,
)
