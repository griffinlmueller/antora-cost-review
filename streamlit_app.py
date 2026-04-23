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

### Instructions
1. Click **⬇️ Download sample tracker CSV** below to get the sample data
2. Upload it using the file uploader
3. Click **▶️ Run Analysis** — takes about 30 seconds
4. View the prioritized findings on screen
5. Download the **color-coded Excel** and **Word summary doc**

> 💡 You can also upload your own cost tracker CSV as long as it has these columns: `id`, `part_name`, `category`, `description`, `material_assumption`, `current_cost_usd`, `savings_estimate_usd`, `status`, `owner`, `last_updated`, `supplier`, `lead_time_weeks`, `notes`, `next_action`
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
st.markdown("## About This Project")

with st.expander("🔧 The Build"):
    st.markdown("""
    This tool was built as a working prototype to demonstrate how AI agents can automate the kind of manual review work that typically falls through the cracks on engineering and ops teams.

    **Stack:**
    - **Python** — core language
    - **Anthropic API (Claude Sonnet)** — the AI backbone that does the analysis
    - **Streamlit** — the web UI wrapper that makes it usable without a terminal
    - **openpyxl** — generates the color-coded Excel output
    - **python-docx** — generates the Word summary doc

    **Why this stack?**
    Claude was chosen because it handles semi-structured data and nuanced reasoning well — identifying that two entries are likely duplicates, for example, requires judgment, not just string matching. Streamlit was chosen to make the tool accessible to anyone without requiring installation or technical setup.

    **The sample data** was built to reflect the kinds of subassemblies and cost categories relevant to Antora's thermal battery products — carbon block components, TPV mounting hardware, thermal insulation, electrical modules — with intentional problems seeded in to demonstrate the agent's detection capabilities.
    """)

with st.expander("⚙️ What the Code Does — Step by Step"):
    st.markdown("""
    The agent runs three sequential calls to Claude. Each step's output feeds directly into the next.

    **Step 1 — Clean & Normalize**
    The raw CSV is passed to Claude with instructions to standardize column names, flag any rows missing critical fields (owner, date, savings estimate), and return structured JSON. This step ensures the downstream analysis is working with clean, consistent data rather than whatever format the tracker happens to be in.

    **Step 2 — Analyze for Issues**
    The cleaned data is passed to a second Claude call that looks for four specific problem types:
    - **Stale entries** — any row with no update in 6+ months (relative to today's date)
    - **Duplicates** — pairs of entries that appear to represent the same part with slightly different names or descriptions
    - **Conflicting assumptions** — entries referencing the same material at different prices, which undermines savings comparisons
    - **High-savings items with no owner** — opportunities above a meaningful savings threshold that have no assigned owner or next action

    **Step 3 — Prioritize**
    The issues found in Step 2 are passed to a third Claude call that acts as a program manager. It produces a ranked list of the top 5 items needing human attention, weighing savings potential against how stalled the entry is. The output is written to be paste-ready into a Slack message or team update.

    **Output generation**
    The results are used to build two downloadable files: an Excel workbook with rows color-coded by issue type (red = stale, orange = duplicate, yellow = conflicting assumption, purple = high savings/no owner), and a Word doc with the executive summary and full findings that can be uploaded to Google Drive to become a Google Doc.
    """)

with st.expander("📊 How Opportunities Are Prioritized"):
    st.markdown("""
    The prioritization logic is intentionally simple and transparent — it's designed to surface the items where inaction is most costly, not just the ones with the highest headline savings number.

    **The core ranking logic:**
    - **Savings × staleness** — a $40k opportunity that hasn't moved in 9 months ranks above a $40k opportunity that was updated last week
    - **No owner = high risk** — unowned items are treated as at-risk regardless of savings size, because without an owner they will not move
    - **Duplicates inflate the tracker** — duplicate entries overstate total pipeline value and create confusion in supplier negotiations, so they are flagged for consolidation regardless of individual savings size
    - **Conflicting assumptions undermine credibility** — if two entries use different $/kg for the same material, neither savings figure can be trusted in a negotiation, so these are flagged even if both entries are otherwise healthy

    **What the agent does not do:**
    The agent does not make decisions — it surfaces information for a human to act on. It does not know which opportunities are strategically important beyond what's in the tracker, it cannot contact suppliers, and it does not update the tracker itself. The goal is to cut the time spent on manual tracker review from hours to minutes, so the human can spend their time on the decisions only they can make.
    """)

st.caption("Built by Griffin Mueller")