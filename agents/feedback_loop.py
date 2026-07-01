import json
import os
from datetime import datetime, timezone

FEEDBACK_LOG_PATH = "logs/feedback_log.jsonl"
EVAL_SET_PATH = "eval/eval_set.json"


def submit_feedback(
    trace_id: str,
    complaint_text: str,
    original_draft: str,
    corrected_draft: str,
    correction_reason: str,
    reviewer_id: str = "human_reviewer",
):
    """
    Logs a human correction on a flagged draft.
    Also appends it to the eval set as a new labeled example
    so future evals benefit from real-world corrections.
    """
    feedback_entry = {
        "trace_id": trace_id,
        "complaint_text": complaint_text,
        "original_draft": original_draft,
        "corrected_draft": corrected_draft,
        "correction_reason": correction_reason,
        "reviewer_id": reviewer_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    os.makedirs("logs", exist_ok=True)
    with open(FEEDBACK_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(feedback_entry) + "\n")

    print(f"  [feedback] Logged correction for trace {trace_id}")
    _append_to_eval_set(complaint_text, correction_reason)
    return feedback_entry


def _append_to_eval_set(complaint_text: str, correction_reason: str):
    """
    Appends a new entry to the eval set based on the human correction.
    Uses 'human_corrected' as a tag so it's distinguishable from
    hand-labeled examples in future eval runs.
    """
    with open(EVAL_SET_PATH, "r", encoding="utf-8") as f:
        eval_set = json.load(f)

    existing_ids = [e["id"] for e in eval_set]
    hc_ids = [e for e in existing_ids if e.startswith("HC")]
    next_num = len(hc_ids) + 1
    new_id = f"HC{next_num:03d}"

    new_entry = {
        "id": new_id,
        "complaint_text": complaint_text,
        "expected_category": "unknown",
        "expected_urgency": "unknown",
        "expected_compliance_flag": False,
        "notes": f"Human-corrected example. Reason: {correction_reason}",
        "source": "human_feedback",
    }

    eval_set.append(new_entry)

    with open(EVAL_SET_PATH, "w", encoding="utf-8") as f:
        json.dump(eval_set, f, indent=2)

    print(f"  [feedback] Added {new_id} to eval set from human correction.")


def load_feedback_log():
    """Returns all feedback entries from the log."""
    entries = []
    if not os.path.exists(FEEDBACK_LOG_PATH):
        return entries
    with open(FEEDBACK_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


if __name__ == "__main__":
    # Simulate a human reviewer correcting a flagged draft
    result = submit_feedback(
        trace_id="db365423-37a5-46e4-bc57-9288995c0a5b",
        complaint_text="I keep getting double charged on my account every month and nobody is helping me.",
        original_draft="We will also apply a one-month service credit.",
        corrected_draft="We have reviewed your account and will process a refund for the duplicate charge within 3-5 business days.",
        correction_reason="Original draft made an unsupported promise about service credit not grounded in policy.",
        reviewer_id="reviewer_001",
    )

    print(f"\nFeedback logged:")
    print(json.dumps(result, indent=2))

    entries = load_feedback_log()
    print(f"\nTotal feedback entries in log: {len(entries)}")