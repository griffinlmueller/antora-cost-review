import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))
from agent import run_analysis
from build_excel import build_excel
from build_doc import build_doc

st.set_page_config(page_title="Antora Cost Tracker Review", layout="wide")

st.title("Antora Cost Tracker — AI Review Agent")
st.caption("Upload a cost opportunity tracker CSV. The agent flags stale entries, duplicates, conflicting assumptions, and high-savings items without owners.")

st.markdown("""
### How it works
1. **Clean** — standardizes fields, flags missing data
2. **Analyze** — identifies the four issue types
3. **Prioritize** — ranks the top actions for human review
""")

st.divider()

with open("data/antora_cost_tracker.csv", "rb") as f:
    st.download_button(
        "⬇️ Download sample tracker CSV",
        f,
        file_name="sample_tracker.csv",
        mime="text/csv"
    )

st.divider()

uploaded = st.file_uploader("Upload your cost tracker CSV", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    st.write(f"Loaded **{len(df)} rows**. Preview:")
    st.dataframe(df.head(5), use_container_width=True)

    if st.button("▶️ Run Analysis", type="primary"):
        with st.spinner("Running AI analysis — takes about 30 seconds..."):
            records = df.to_dict(orient="records")
            result = run_analysis(records)
            st.session_state["result"] = result
            st.session_state["df"] = df

if "result" in st.session_state:
    result = st.session_state["result"]
    df = st.session_state["df"]

    st.success("✅ Analysis complete!")

    st.subheader("Executive Summary")
    st.write(result["priorities"]["summary"])

    st.subheader("Top Priorities")
    for item in result["priorities"]["top_priorities"]:
        with st.expander(f"{item['rank']}. {item['title']}"):
            st.write(f"**Why:** {item['why']}")
            st.write(f"**Recommended action:** {item['recommended_action']}")
            if item.get("owner_suggestion"):
                st.write(f"**Suggested owner:** {item['owner_suggestion']}")
            st.write(f"**Related IDs:** {', '.join(item['related_ids'])}")

    st.subheader("Issues Found")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔴 Stale entries", len(result["issues"]["stale_entries"]))
    col2.metric("🟠 Duplicates", len(result["issues"]["duplicates"]))
    col3.metric("🟡 Assumption conflicts", len(result["issues"]["conflicting_assumptions"]))
    col4.metric("🟣 High savings, no owner", len(result["issues"]["high_savings_no_owner"]))

    st.subheader("Download Reports")
    excel_buf = build_excel(df, result["issues"])
    doc_buf = build_doc(result["priorities"], result["issues"])

    col1, col2 = st.columns(2)
    col1.download_button(
        "📊 Download Excel (highlighted issues)",
        excel_buf,
        file_name="cost_tracker_review.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    col2.download_button(
        "📄 Download Word Doc (upload to Google Drive → Google Doc)",
        doc_buf,
        file_name="cost_tracker_review.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

st.divider()
st.caption("Built by Griffin Mueller")