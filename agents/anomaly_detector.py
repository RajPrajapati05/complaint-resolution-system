import json
import os
from collections import defaultdict
from datetime import datetime, timezone

LOG_PATH = "logs/pipeline.jsonl"
ANOMALY_RESULTS_PATH = "logs/anomaly_report.json"

# If any category exceeds this share of total complaints, flag it as a spike
SPIKE_THRESHOLD_PCT = 0.5  # 50% of all complaints in the window


def load_router_events(log_path=LOG_PATH):
    """Read all router-stage entries from the JSONL pipeline log."""
    events = []
    if not os.path.exists(log_path):
        return events
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("stage") == "router":
                    events.append(entry)
            except json.JSONDecodeError:
                continue
    return events


def detect_anomalies(events):
    """
    Counts complaints per category and flags any category that exceeds
    SPIKE_THRESHOLD_PCT of total volume as a potential spike.
    """
    category_counts = defaultdict(int)
    compliance_counts = defaultdict(int)
    total = len(events)

    for event in events:
        data = event.get("data", {})
        category = data.get("category", "unknown")
        compliance = data.get("compliance_flag", False)
        category_counts[category] += 1
        if compliance:
            compliance_counts[category] += 1

    if total == 0:
        return {
            "total_complaints_analyzed": 0,
            "anomalies_detected": [],
            "category_distribution": {},
            "compliance_distribution": {},
            "message": "No router events found in log.",
        }

    distribution = {
        cat: {
            "count": count,
            "pct": round(count / total * 100, 1),
            "compliance_flagged": compliance_counts.get(cat, 0),
        }
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])
    }

    anomalies = []
    for cat, stats in distribution.items():
        if stats["pct"] >= SPIKE_THRESHOLD_PCT * 100:
            anomalies.append({
                "category": cat,
                "count": stats["count"],
                "pct": stats["pct"],
                "severity": "high" if stats["pct"] >= 70 else "medium",
                "message": (
                    f"Spike detected: '{cat}' accounts for {stats['pct']}% "
                    f"of complaints in the current window."
                ),
            })

    return {
        "total_complaints_analyzed": total,
        "anomalies_detected": anomalies,
        "category_distribution": distribution,
        "compliance_distribution": dict(compliance_counts),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_anomaly_detection():
    events = load_router_events()
    report = detect_anomalies(events)

    os.makedirs("logs", exist_ok=True)
    with open(ANOMALY_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"\n=== ANOMALY DETECTION REPORT ===")
    print(f"Total complaints analyzed: {report['total_complaints_analyzed']}")
    print(f"\nCategory distribution:")
    for cat, stats in report["category_distribution"].items():
        flag = " ** SPIKE **" if any(
            a["category"] == cat for a in report["anomalies_detected"]
        ) else ""
        print(f"  {cat}: {stats['count']} ({stats['pct']}%) "
              f"[{stats['compliance_flagged']} compliance flagged]{flag}")

    if report["anomalies_detected"]:
        print(f"\nAnomalies detected ({len(report['anomalies_detected'])}):")
        for a in report["anomalies_detected"]:
            print(f"  [{a['severity'].upper()}] {a['message']}")
    else:
        print("\nNo anomalies detected.")

    print(f"\nReport saved to {ANOMALY_RESULTS_PATH}")
    return report


if __name__ == "__main__":
    run_anomaly_detection()