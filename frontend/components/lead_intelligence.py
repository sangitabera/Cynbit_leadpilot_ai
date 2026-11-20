
import streamlit as st


def render_list_section(title: str, items: list, icon: str):
    st.markdown(f"#### {icon} {title}")

    if items:
        for item in items:
            st.markdown(f"- {item}")
    else:
        st.caption("No information identified.")


def render_lead_intelligence(lead: dict):
    """Render AI-generated lead intelligence."""

    if not isinstance(lead, dict):
        st.warning("Lead information is unavailable.")
        return

    intelligence = lead.get("lead_intelligence") or {}
    services = lead.get("service_matches") or []

    st.markdown("## 🧠 AI Lead Intelligence")

    if not intelligence:
        st.info(
            "AI intelligence is not available for this lead. "
            "Please review the enquiry manually."
        )
        return

    # -------------------------------------------------
    # 1. Lead overview
    # -------------------------------------------------

    priority = lead.get("priority", "Unknown")
    score = lead.get("priority_score", 0)

    intent = intelligence.get("buying_intent", "Unclear")
    urgency = intelligence.get("urgency", "Unknown")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Lead Score",
        f"{score}/100",
    )

    col2.metric(
        "Priority",
        priority,
    )

    col3.metric(
        "Buying Intent",
        intent,
    )

    col4.metric(
        "Urgency",
        urgency,
    )

    st.divider()

    # -------------------------------------------------
    # 2. Recommended service
    # -------------------------------------------------

    st.markdown("### 🎯 Recommended Cynbit Service")

    st.success(
        intelligence.get(
            "recommended_service",
            "Needs clarification",
        )
    )

    st.write(
        intelligence.get(
            "service_match_reason",
            "No explanation available.",
        )
    )

    # -------------------------------------------------
    # 3. Customer intelligence
    # -------------------------------------------------

    left, right = st.columns(2)

    with left:
        render_list_section(
            "Customer Pain Points",
            intelligence.get("pain_points", []),
            "🔴",
        )

        render_list_section(
            "Buying Signals",
            intelligence.get("buying_signals", []),
            "🟢",
        )

    with right:
        render_list_section(
            "Business Requirements",
            intelligence.get("business_requirements", []),
            "📋",
        )

        render_list_section(
            "Missing Information",
            intelligence.get("missing_information", []),
            "❓",
        )

    st.divider()

    # -------------------------------------------------
    # 4. Risk analysis
    # -------------------------------------------------

    st.markdown("### ⚠️ Risk Analysis")

    risks = intelligence.get("potential_risks", [])

    if risks:
        for risk in risks:
            st.warning(risk)
    else:
        st.success("No potential risks identified by the analysis.")

    # -------------------------------------------------
    # 5. Service retrieval
    # -------------------------------------------------

    st.markdown("### 🔎 Relevant Cynbit Services")

    if services:
        for service in services:
            with st.container(border=True):
                st.markdown(
                    f"**{service.get('service_name', 'Unknown service')}**"
                )

                st.caption(
                    service.get("category", "")
                )

                st.write(
                    service.get("description", "")
                )

                relevance = service.get(
                    "relevance_score",
                    0,
                )

                st.progress(
                    min(max(float(relevance), 0.0), 1.0),
                    text=f"Retrieval relevance: {relevance:.2%}",
                )
    else:
        st.info("No matching services were retrieved.")

    st.divider()

    # -------------------------------------------------
    # 6. Recommended action
    # -------------------------------------------------

    st.markdown("### 🚀 Recommended Next Action")

    st.info(
        intelligence.get(
            "recommended_next_action",
            lead.get("recommended_action", "Manual review required."),
        )
    )

    with st.expander("View AI reasoning"):
        st.write(
            intelligence.get(
                "reasoning",
                "No reasoning provided.",
            )
        )

    with st.expander("View generated follow-up email"):
        st.text_area(
            "Follow-up email",
            value=lead.get("followup_email", ""),
            height=220,
            disabled=True,
        )

    st.caption(
        "AI-generated insights are recommendations and should be "
        "reviewed by a human before contacting a lead."
    )
