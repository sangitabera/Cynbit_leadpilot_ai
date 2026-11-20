
import pandas as pd
import plotly.express as px
import streamlit as st


def render_analytics(leads: list):
    st.title("📊 Lead Intelligence Analytics")
    st.caption(
        "Understand lead quality, demand, and pipeline distribution."
    )

    if not leads:
        st.info("No leads available. Analyze some leads first.")
        return

    df = pd.DataFrame(leads)

    if "result_json" in df.columns:
        details = df["result_json"].apply(
            lambda x: x if isinstance(x, dict) else {}
        )
        details_df = pd.json_normalize(details)
        df = pd.concat(
            [df.drop(columns=["result_json"]), details_df],
            axis=1,
        )

    def get_column(name, default):
        if name in df.columns:
            return df[name].fillna(default)
        return pd.Series([default] * len(df), index=df.index)

    priority = get_column("priority", "Unknown")
    scores = pd.to_numeric(
        get_column("priority_score", 0),
        errors="coerce",
    ).fillna(0)

    intent = get_column(
        "lead_intelligence.buying_intent",
        "Unclear",
    )

    service = get_column(
        "lead_intelligence.recommended_service",
        "Unclassified",
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Leads", len(df))
    col2.metric("High Priority", int((priority == "High").sum()))
    col3.metric("Average Score", f"{scores.mean():.1f}/100")
    col4.metric("High Intent", int((intent == "High").sum()))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Lead Priority Distribution")

        priority_counts = priority.value_counts().reset_index()
        priority_counts.columns = ["Priority", "Leads"]

        fig = px.pie(
            priority_counts,
            names="Priority",
            values="Leads",
            hole=0.55,
            title="Lead priority breakdown",
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Lead Score Distribution")

        fig = px.histogram(
            x=scores,
            nbins=10,
            labels={"x": "Lead Score"},
            title="Lead score distribution",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Service Demand")

        service_counts = service.value_counts().reset_index()
        service_counts.columns = ["Service", "Leads"]

        fig = px.bar(
            service_counts,
            x="Service",
            y="Leads",
            title="Recommended service distribution",
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Buying Intent")

        intent_counts = intent.value_counts().reset_index()
        intent_counts.columns = ["Intent", "Leads"]

        fig = px.bar(
            intent_counts,
            x="Intent",
            y="Leads",
            title="Buying intent distribution",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Lead Records")

    display_columns = [
        column
        for column in [
            "id",
            "name",
            "company",
            "priority",
            "priority_score",
            "approval_status",
        ]
        if column in df.columns
    ]

    if display_columns:
        st.dataframe(
            df[display_columns],
            use_container_width=True,
            hide_index=True,
        )

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download Analytics CSV",
        data=csv,
        file_name="leadpilot_analytics.csv",
        mime="text/csv",
    )
