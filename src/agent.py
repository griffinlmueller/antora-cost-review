import anthropic
import pandas as pd
import json
import os
from pathlib import Path

import streamlit as st

if "ANTHROPIC_API_KEY" in st.secrets:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
else:
    api_key = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=api_key)
MODEL = "claude-sonnet-4-6"

def load_tracker(path):
    df = pd.read_csv(path)
    return df.to_dict(orient="records")

def call_claude(system_prompt, user_content, max_tokens=4000):
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )
    return response.content[0].text

def clean_data(tracker_data):
    system = """You are a data cleaning assistant for a cost opportunity tracker at an industrial hardware company.
Standardize the data and flag rows missing critical fields.
Return valid JSON only with structure: {"cleaned": [...], "missing_fields": [{"id": "...", "fields_missing": [...]}]}
Do not add commentary."""
    user = f"Clean this tracker data:\n\n{json.dumps(tracker_data, indent=2)}"
    result = call_claude(system, user, max_tokens=8000)
    result = call_claude(system, user, max_tokens=8000)
    cleaned = result.strip()
    if "```" in cleaned:
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())

def analyze_issues(cleaned_data):
    system = """You are a cost analyst reviewing a tracker of cost-reduction opportunities for an industrial thermal battery manufacturer.
Analyze the data and identify four categories of issues. Return JSON only:
{
  "stale_entries": [{"id": "...", "part_name": "...", "last_updated": "...", "days_stale": N, "savings": N}],
  "duplicates": [{"ids": ["...", "..."], "reason": "..."}],
  "conflicting_assumptions": [{"ids": ["...", "..."], "conflict": "..."}],
  "high_savings_no_owner": [{"id": "...", "part_name": "...", "savings": N}]
}
Stale = no update in 6+ months (today is April 22, 2026).
Duplicates = same part with slightly different names or descriptions.
Conflicting = same material referenced at different prices across entries."""
    user = f"Analyze this tracker:\n\n{json.dumps(cleaned_data, indent=2)}"
    result = call_claude(system, user, max_tokens=6000)
    result = call_claude(system, user)
    cleaned = result.strip()
    if "```" in cleaned:
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())

def prioritize(issues, cleaned_data):
    system = """You are a program manager writing a monthly cost-reduction review summary for Antora Energy's product development team.
Based on the issues analysis, produce a prioritized action list. Return JSON only:
{
  "top_priorities": [{"rank": N, "title": "...", "why": "...", "recommended_action": "...", "owner_suggestion": "...", "related_ids": [...]}],
  "summary": "2-3 sentence executive summary of the tracker's current state"
}
Rank by impact: highest savings x most stalled gets top priority. Include 5 items max."""
    user = f"Issues found:\n{json.dumps(issues, indent=2)}\n\nTracker context:\n{json.dumps(cleaned_data[:5], indent=2)}"
    result = call_claude(system, user)
    result = call_claude(system, user)
    cleaned = result.strip()
    if "```" in cleaned:
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())

def run_analysis(tracker_records):
    cleaned = clean_data(tracker_records)
    issues = analyze_issues(cleaned["cleaned"])
    priorities = prioritize(issues, cleaned["cleaned"])
    return {"cleaned": cleaned, "issues": issues, "priorities": priorities}