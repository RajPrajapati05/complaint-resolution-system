import os
import json
import time
import uuid
from datetime import datetime, timezone

from agents.versioning import log_version_event
from agents.router_agent import RouterAgent
from agents.retrieval_agent import RetrievalAgent
from agents.drafting_agent import DraftingAgent
from agents.critique_agent import CritiqueAgent

LOG_PATH = "logs/pipeline.jsonl"


class Orchestrator:
    def __init__(self):
        print("[orchestrator] Initializing agents...")
        self.router = RouterAgent()
        self.retrieval = RetrievalAgent()
        self.drafting = DraftingAgent()
        self.critique = CritiqueAgent()
        print("[orchestrator] All agents ready.")

    def _log_stage(self, trace_id, stage, duration_ms, data):
        entry = {
            "trace_id": trace_id,
            "stage": stage,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": round(duration_ms, 2),
            "data": data,
        }
        os.makedirs("logs", exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def process_complaint(self, complaint_text: str) -> dict:
        trace_id = str(uuid.uuid4())
        pipeline_start = time.time()

        # Stage 1: Router
        t0 = time.time()
        route_result = self.router.route(complaint_text)
        self._log_stage(trace_id, "router", (time.time() - t0) * 1000, route_result)

        # Stage 2: Retrieval
        t0 = time.time()
        retrieval_result = self.retrieval.retrieve(complaint_text)
        self._log_stage(trace_id, "retrieval", (time.time() - t0) * 1000, retrieval_result)

        # Stage 3: Drafting
        t0 = time.time()
        draft_result = self.drafting.draft(complaint_text, retrieval_result)
        self._log_stage(trace_id, "drafting", (time.time() - t0) * 1000, draft_result)

        # Stage 4: Critique
        t0 = time.time()
        critique_result = self.critique.critique(
            complaint_text=complaint_text,
            compliance_flag=route_result.get("compliance_flag", False),
            retrieval_result=retrieval_result,
            draft_result=draft_result,
        )
        self._log_stage(trace_id, "critique", (time.time() - t0) * 1000, critique_result)

        total_duration_ms = (time.time() - pipeline_start) * 1000

        final_status = (
            "auto_approved" if critique_result.get("decision") == "auto_approve"
            else "routed_to_human_review"
        )

        log_version_event(trace_id, "router", route_result.get("_model_used", "unknown"))
        log_version_event(trace_id, "drafting", draft_result.get("_model_used", "unknown"))
        log_version_event(trace_id, "critique", critique_result.get("_model_used", "unknown"))

        self._log_stage(trace_id, "pipeline_complete", total_duration_ms, {"final_status": final_status})

        result = {
            "trace_id": trace_id,
            "complaint_text": complaint_text,
            "routing": route_result,
            "retrieval": retrieval_result,
            "draft": draft_result,
            "critique": critique_result,
            "final_status": final_status,
            "total_duration_ms": round(total_duration_ms, 2),
        }

        return result


if __name__ == "__main__":
    orchestrator = Orchestrator()

    test_complaint = "I keep getting double charged on my account every month and nobody is helping me."
    result = orchestrator.process_complaint(test_complaint)

    print("\n=== FINAL RESULT ===")
    print(json.dumps(result, indent=2))