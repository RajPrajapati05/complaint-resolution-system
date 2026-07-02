import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import streamlit as st
import pandas as pd
from collections import defaultdict

from agents.monitoring import load_all_events, run_monitoring
from agents.anomaly_detector import load_router_events, detect_anomalies

st.set_page_config(
    page_title="Complaint Resolution Dashboard",
    page_icon="📋",
    layout="wide",
)

st.title("📋 Consumer Complaint Resolution System")
st.caption("Live monitoring dashboard — reads from pipeline JSONL logs")

# Refresh button
if st.button("🔄 Refresh Data"):
    st.rerun()

# Load data
events = load_all_events()
router_events = [e for e in events if e.get("stage") == "router"]
pipeline_events = [e for e in events if e.get("stage") == "pipeline_complete"]
stage_events = [e for e in events if e.get("stage") in
                ["router", "retrieval", "drafting", "critique"]]

if not events:
    st.warning("No pipeline logs found. Run some complaints through the API first.")
    st.stop()

# --- TOP METRICS ROW ---
col1, col2, col3, col4 = st.columns(4)

total_pipelines = len(pipeline_events)
auto_approved = sum(
    1 for e in pipeline_events
    if e.get("data", {}).get("final_status") == "auto_approved"
)
human_review = total_pipelines - auto_approved
compliance_flagged = sum(
    1 for e in router_events
    if e.get("data", {}).get("compliance_flag") is True
)

col1.metric("Total Complaints Processed", total_pipelines)
col2.metric("Auto Approved", auto_approved)
col3.metric("Routed to Human Review", human_review)
col4.metric("Compliance Flagged", compliance_flagged)

st.divider()

# --- CATEGORY DISTRIBUTION ---
left, right = st.columns(2)

with left:
    st.subheader("Complaint Category Distribution")
    category_counts = defaultdict(int)
    for e in router_events:
        cat = e.get("data", {}).get("category", "unknown")
        category_counts[cat] += 1

    if category_counts:
        df_cat = pd.DataFrame(
            list(category_counts.items()),
            columns=["Category", "Count"]
        ).sort_values("Count", ascending=False)
        st.bar_chart(df_cat.set_index("Category"))
    else:
        st.info("No category data yet.")

with right:
    st.subheader("Urgency Distribution")
    urgency_counts = defaultdict(int)
    for e in router_events:
        urg = e.get("data", {}).get("urgency", "unknown")
        urgency_counts[urg] += 1

    if urgency_counts:
        df_urg = pd.DataFrame(
            list(urgency_counts.items()),
            columns=["Urgency", "Count"]
        ).sort_values("Count", ascending=False)
        st.bar_chart(df_urg.set_index("Urgency"))
    else:
        st.info("No urgency data yet.")

st.divider()

# --- LATENCY PER STAGE ---
st.subheader("Average Latency per Pipeline Stage (ms)")

stage_latencies = defaultdict(list)
for e in stage_events:
    stage = e.get("stage")
    duration = e.get("duration_ms")
    if stage and duration is not None:
        stage_latencies[stage].append(duration)

if stage_latencies:
    stage_order = ["router", "retrieval", "drafting", "critique"]
    latency_data = {
        stage: round(sum(vals) / len(vals), 2)
        for stage, vals in stage_latencies.items()
        if stage in stage_order
    }
    df_lat = pd.DataFrame(
        list(latency_data.items()),
        columns=["Stage", "Avg Latency (ms)"]
    )
    df_lat["Stage"] = pd.Categorical(
        df_lat["Stage"], categories=stage_order, ordered=True
    )
    df_lat = df_lat.sort_values("Stage")
    st.bar_chart(df_lat.set_index("Stage"))
else:
    st.info("No latency data yet.")

st.divider()

# --- ANOMALY DETECTION ---
st.subheader("Anomaly Detection")
anomaly_report = detect_anomalies(router_events)

if anomaly_report["anomalies_detected"]:
    for anomaly in anomaly_report["anomalies_detected"]:
        severity = anomaly["severity"]
        color = "🔴" if severity == "high" else "🟡"
        st.warning(f"{color} [{severity.upper()}] {anomaly['message']}")
else:
    st.success("✅ No anomalies detected in current window.")

st.divider()

# --- RECENT PIPELINE RUNS ---
st.subheader("Recent Pipeline Runs")

recent_runs = []
seen_traces = set()
for e in reversed(events):
    if e.get("stage") == "pipeline_complete":
        tid = e.get("trace_id")
        if tid not in seen_traces:
            seen_traces.add(tid)
            recent_runs.append({
                "Trace ID": tid[:8] + "...",
                "Final Status": e.get("data", {}).get("final_status", "unknown"),
                "Duration (ms)": e.get("duration_ms"),
                "Timestamp": e.get("timestamp", "")[:19].replace("T", " "),
            })
        if len(recent_runs) >= 10:
            break

if recent_runs:
    st.dataframe(pd.DataFrame(recent_runs), use_container_width=True)
else:
    st.info("No completed pipeline runs found.")

st.divider()
st.caption("Data sourced from logs/pipeline.jsonl — refresh to update.")