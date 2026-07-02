import json
import os
from datetime import datetime, timezone

VERSION_LOG_PATH = "logs/version_log.jsonl"

# Increment PROMPT_VERSION manually whenever you change a prompt template
# Format: "v{major}.{minor}" — bump minor for small tweaks, major for rewrites
PROMPT_VERSIONS = {
    "router": "v1.0",
    "drafting": "v1.0",
    "critique": "v1.0",
}


def get_version_tag(agent_name: str, model_used: str) -> dict:
    """
    Returns a version tag dict to attach to any pipeline output.
    Call this from each agent to stamp its output with versioning metadata.
    """
    return {
        "agent": agent_name,
        "prompt_version": PROMPT_VERSIONS.get(agent_name, "v1.0"),
        "model_used": model_used,
        "tagged_at": datetime.now(timezone.utc).isoformat(),
    }


def log_version_event(trace_id: str, agent_name: str, model_used: str):
    """
    Appends a version event to the version log.
    Called automatically by the orchestrator for each pipeline run.
    """
    entry = {
        "trace_id": trace_id,
        "agent": agent_name,
        "prompt_version": PROMPT_VERSIONS.get(agent_name, "v1.0"),
        "model_used": model_used,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs("logs", exist_ok=True)
    with open(VERSION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def load_version_history():
    """Returns all version log entries."""
    entries = []
    if not os.path.exists(VERSION_LOG_PATH):
        return entries
    with open(VERSION_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def summarize_version_history():
    """Prints a summary of which prompt versions and models have been used."""
    entries = load_version_history()
    if not entries:
        print("No version history found.")
        return

    from collections import defaultdict
    combos = defaultdict(int)
    for e in entries:
        key = f"{e['agent']} | prompt={e['prompt_version']} | model={e['model_used']}"
        combos[key] += 1

    print(f"\n=== VERSION HISTORY SUMMARY ===")
    print(f"Total version events logged: {len(entries)}")
    print(f"\nAgent/prompt/model combinations seen:")
    for combo, count in sorted(combos.items()):
        print(f"  {combo}  ({count} runs)")


if __name__ == "__main__":
    # Simulate logging version events for a pipeline run
    fake_trace_id = "test-trace-versioning-001"

    log_version_event(fake_trace_id, "router", "gemini-2.5-flash-lite")
    log_version_event(fake_trace_id, "drafting", "gemini-2.5-flash")
    log_version_event(fake_trace_id, "critique", "gemini-2.5-flash")

    summarize_version_history()