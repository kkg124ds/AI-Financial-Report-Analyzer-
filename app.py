"""Streamlit interface for the AI Financial Report Analyzer."""

import json

import pandas as pd
import streamlit as st

from analyzer import analyze_report


st.set_page_config(page_title="AI Financial Report Analyzer", page_icon="📊", layout="wide")
st.title("📊 AI Financial Report Analyzer")
st.write(
    "Upload a financial report to get an evidence-linked extractive summary, "
    "selected metric comparisons, and review cues."
)
st.info(
    "This learning prototype uses local text extraction, TF-IDF sentence ranking, "
    "and transparent rules. It is not investment advice or a substitute for accountant review."
)

with st.expander("What this tool can and cannot do"):
    st.markdown(
        """
        **Can:** read selectable text in PDFs or UTF-8 text files, rank important sentences,
        compare selected financial metric rows, and surface report wording for a person to review.

        **Cannot:** reliably read scanned-image PDFs, understand every company’s table layout,
        verify whether an explanation is true, forecast share prices, or replace professional analysis.
        """
    )

uploaded = st.file_uploader(
    "Choose a report",
    type=["pdf", "txt"],
    help="For the first run, try the included fictional sample_report.txt.",
)
sentence_count = st.slider("Summary length (sentences)", min_value=3, max_value=8, value=5)

if uploaded is None:
    st.caption("The included sample_report.txt is fictional and intended only for trying the app.")
    st.stop()

if st.button("Analyze report", type="primary"):
    with st.spinner("Reading and analyzing the report…"):
        try:
            result = analyze_report(uploaded.name, uploaded.getvalue(), sentence_count)
            st.session_state["analysis_result"] = result
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

result = st.session_state.get("analysis_result")
if result and result.get("filename") == uploaded.name:
    st.caption(f"Analyzed {result['page_count']} page(s) · {result['character_count']:,} extracted characters")

    st.subheader("Concise summary")
    if result["summary"]:
        for item in result["summary"]:
            st.markdown(f"- {item['text']} **(p. {item['page']})**")
    else:
        st.warning("No readable sentences were found in this document.")

    st.subheader("Financial metrics found")
    if result["metrics"]:
        rows = []
        for item in result["metrics"]:
            rows.append({
                "Metric": item["metric"],
                "Latest period": item["current_period"],
                "Latest value (as reported)": item["current_as_reported"],
                "Prior period": item["previous_period"],
                "Prior value (as reported)": item["previous_as_reported"] or "Not found",
                "Change": f"{item['change_pct']:+.1f}%" if item["change_pct"] is not None else "Not calculated",
                "Page": item["page"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        with st.expander("Show source lines used for metric extraction"):
            for item in result["metrics"]:
                st.markdown(f"**{item['metric']} · page {item['page']}**")
                st.code(item["evidence"])
    else:
        st.warning("No supported metric rows were recognized. Check the extracted PDF text or try the sample report.")

    left, right = st.columns(2)
    with left:
        st.subheader("Metric change signals")
        if result["metric_signals"]:
            for signal in result["metric_signals"]:
                prefix = "⚠️ Risk review" if signal["type"] == "risk" else "✅ Potential positive signal"
                st.markdown(f"**{prefix}: {signal['title']}** · page {signal['page']}")
                st.write(signal["detail"])
                st.caption(f"Evidence: {signal['evidence']}")
        else:
            st.write("No configured metric-change rules were triggered by the values found.")

    with right:
        st.subheader("Disclosure wording to review")
        if result["disclosure_cues"]:
            for cue in result["disclosure_cues"]:
                st.markdown(f"**{cue['type'].title()} cue: “{cue['term']}”** · page {cue['page']}")
                st.caption(cue["evidence"])
        else:
            st.write("No configured wording cues were found.")

    export = json.dumps(result, indent=2, ensure_ascii=False)
    st.download_button(
        "Download analysis as JSON",
        data=export,
        file_name="financial_report_analysis.json",
        mime="application/json",
    )
