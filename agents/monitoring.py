import json
import os
from collections import defaultdict
from datetime import datetime, timezone

LOG_PATH = "logs/pipeline.jsonl"
MONITORING_REPORT_PATH = "logs/monitoring_report.json"

STAGES = ["router", "retrieval", "drafting", "critique", "pipeline_complete"]


def load_all_events(log_path=LOG_PATH):
    events = []
    if not os.path.exists(log_path):
        return events
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def compute_stats(values):
    if not values:
        return {"count": 0, "mean_ms": None, "min_ms": None, "max_ms": None}
    return {
        "count": len(values),
        "mean_ms": round(sum(values) / len(values), 2),
        "min_ms": round(min(values), 2),
        "max_ms": round(max(values), 2),
    }


def run_monitoring():
    events = load_all_events()

    stage_latencies = defaultdict(list)
    model_usage = defaultdict(int)
    final_statuses = defaultdict(int)
    compliance_flags = 0
    total_pipelines = 0

    for event in events:
        stage = event.get("stage")
        duration = event.get("duration_ms")
        data = event.get("data", {})

        if stage in STAGES and duration is not None:
            stage_latencies[stage].append(duration)

        if stage == "router":
            model = data.get("_model_used")
            if model:
                model_usage[model] += 1
            if data.get("compliance_flag"):
                compliance_flags += 1

        if stage == "drafting":
            model = data.get("_model_used")
            if model:
                model_usage[model] += 1

        if stage == "critique":
            model = data.get("_model_used")
            if model:
                model_usage[model] += 1

        if stage == "pipeline_complete":
            total_pipelines += 1
            status = data.get("final_status", "unknown")
            final_statuses[status] += 1

    stage_stats = {
        stage: compute_stats(stage_latencies[stage])
        for stage in STAGES
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_pipelines_run": total_pipelines,
        "final_status_distribution": dict(final_statuses),
        "compliance_flag_rate": (
            round(compliance_flags / max(total_pipelines, 1) * 100, 1)
        ),
        "stage_latency_stats_ms": stage_stats,
        "model_usage_counts": dict(model_usage),
    }

    os.makedirs("logs", exist_ok=True)
    with open(MONITORING_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n=== MONITORING REPORT ===")
    print(f"Total pipelines run:     {total_pipelines}")
    print(f"Compliance flag rate:    {report['compliance_flag_rate']}%")
    print(f"\nFinal status distribution:")
    for status, count in final_statuses.items():
        print(f"  {status}: {count}")

    print(f"\nStage latency (ms):")
    for stage, stats in stage_stats.items():
        if stats["count"] > 0:
            print(f"  {stage:<20} mean={stats['mean_ms']}ms  "
                  f"min={stats['min_ms']}ms  max={stats['max_ms']}ms  "
                  f"(n={stats['count']})")

    print(f"\nModel usage counts:")
    for model, count in model_usage.items():
        print(f"  {model}: {count} calls")

    print(f"\nReport saved to {MONITORING_REPORT_PATH}")
    return report


if __name__ == "__main__":
    run_monitoring()