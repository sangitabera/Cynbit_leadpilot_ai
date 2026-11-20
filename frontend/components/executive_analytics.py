
import pandas as pd
import plotly.express as px
import streamlit as st


def render_executive_analytics(summary: dict):
    st.title("Executive Intelligence Dashboard")
    st.caption(
        "Real-time overview of lead quality, approval decisions "
        "and sales pipeline progress."
    )

    if not isinstance(summary, dict):
        st.error("Invalid analytics response.")
        return

    total = summary.get("total_leads", 0)
    converted = summary.get("converted_leads", 0)
    lost = summary.get("lost_leads", 0)

    lifecycle = summary.get("lifecycle_distribution", {})
    approvals = summary.get("approval_distribution", {})
    priorities = summary.get("priority_distribution", {})

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Leads", total)
    col2.metric("Converted", converted)
    col3.metric("Lost", lost)
    col4.metric(
        "Pending Approval",
        approvals.get("Pending", 0),
    )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Lead Lifecycle Distribution")

        if lifecycle:
            lifecycle_df = pd.DataFrame(
                list(lifecycle.items()),
                columns=["Stage", "Leads"],
            )

            fig = px.pie(
                lifecycle_df,
                names="Stage",
                values="Leads",
                hole=0.55,
                title="Pipeline Distribution",
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No lifecycle data available.")

    with col2:
        st.subheader("Lead Priority Distribution")

        if priorities:
            priority_df = pd.DataFrame(
                list(priorities.items()),
                columns=["Priority", "Leads"],
            )

            fig = px.bar(
                priority_df,
                x="Priority",
                y="Leads",
                color="Priority",
                title="AI Lead Priority",
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No priority data available.")

    st.divider()

    st.subheader("Human Approval Distribution")

    if approvals:
        approval_df = pd.DataFrame(
            list(approvals.items()),
            columns=["Decision", "Leads"],
        )

        fig = px.bar(
            approval_df,
            x="Decision",
            y="Leads",
            title="Human Review Decisions",
            text="Leads",
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No approval data available.")

    st.divider()

    conversion_rate = (
        converted / total * 100 if total else 0
    )

    st.subheader("Conversion Tracking")

    st.metric(
        "Recorded Conversion Rate",
        f"{conversion_rate:.1f}%",
        help=(
            "Calculated from leads explicitly marked Converted. "
            "This is an observed pipeline metric, not an AI prediction."
        ),
    )

    st.caption(
        "Metrics describe recorded lead statuses. "
        "They do not represent predicted conversion probabilities."
    )
