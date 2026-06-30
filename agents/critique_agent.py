import os
import json
from dotenv import load_dotenv
from google import genai

from agents.config import CRITIQUE_MODEL
from agents.gemini_client import call_gemini_json

load_dotenv()

CRITIQUE_PROMPT_TEMPLATE = """You are a compliance and quality reviewer for customer support responses.
You independently verify drafts before they are sent to customers - do not simply trust the drafter's claims.

Original customer complaint:
\"\"\"{complaint_text}\"\"\"

Compliance flag from intake routing: {compliance_flag}

Precedent cases that were available for grounding (the ONLY legitimate source of specific
promises like refund amounts, timelines, or policy details):
{precedent_block}

Draft response to review:
\"\"\"{draft_response}\"\"\"

Precedent IDs the drafter claims to have used: {claimed_precedent_ids}

Independently check the draft against the precedents above and evaluate:
1. unsupported_claims: does the draft state any specific promise (refund amount, timeline,
   policy detail, legal commitment) that is NOT actually backed by the precedent text shown?
   List each unsupported claim found, or an empty list if none.
2. tone_issues: is the tone unprofessional, dismissive, overly robotic, or lacking empathy?
   List specific issues found, or an empty list if none.
3. missing_compliance_ack: if compliance_flag is true, does the draft fail to acknowledge
   the seriousness of the issue (e.g. ignores mentions of legal action, safety, discrimination)?
   true or false. If compliance_flag is false, always return false here.

Respond with ONLY a JSON object in exactly this shape:
{{
  "unsupported_claims": ["list of strings, empty if none"],
  "tone_issues": ["list of strings, empty if none"],
  "missing_compliance_ack": true or false,
  "decision": "auto_approve" or "human_review",
  "decision_reason": "one sentence explaining the decision"
}}

Decision rule: if unsupported_claims is non-empty, OR tone_issues is non-empty, OR
missing_compliance_ack is true, the decision MUST be "human_review". Otherwise "auto_approve".
"""


class CritiqueAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")
        self.client = genai.Client(api_key=api_key)

    def critique(self, complaint_text: str, compliance_flag: bool,
                 retrieval_result: dict, draft_result: dict) -> dict:

        # Drafts that were never grounded (no precedent found) always go to human review -
        # no need to spend a critique call on them.
        if not draft_result.get("grounded", False):
            return {
                "unsupported_claims": [],
                "tone_issues": [],
                "missing_compliance_ack": False,
                "decision": "human_review",
                "decision_reason": "Draft was ungrounded (no precedent found); requires human review by design.",
                "_model_used": None,
            }

        precedents = retrieval_result.get("precedents", [])
        precedent_block = "\n".join(
            f"- [{p['id']}] Complaint: \"{p['complaint_text']}\" | Resolution: \"{p['resolution']}\""
            for p in precedents
        ) or "(none)"

        prompt = CRITIQUE_PROMPT_TEMPLATE.format(
            complaint_text=complaint_text,
            compliance_flag=compliance_flag,
            precedent_block=precedent_block,
            draft_response=draft_result.get("draft_response", ""),
            claimed_precedent_ids=draft_result.get("precedent_ids_used", []),
        )

        raw_response, model_used = call_gemini_json(
            client=self.client,
            model=CRITIQUE_MODEL,
            prompt=prompt,
        )

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            raise ValueError(f"Critique agent returned invalid JSON: {raw_response}")

        # Enforce the decision rule in code too, don't fully trust the model's own decision field
        has_issues = (
            bool(result.get("unsupported_claims"))
            or bool(result.get("tone_issues"))
            or result.get("missing_compliance_ack", False)
        )
        result["decision"] = "human_review" if has_issues else "auto_approve"
        result["_model_used"] = model_used
        return result


if __name__ == "__main__":
    from agents.retrieval_agent import RetrievalAgent
    from agents.drafting_agent import DraftingAgent

    retrieval_agent = RetrievalAgent()
    drafting_agent = DraftingAgent()
    critique_agent = CritiqueAgent()

    test_complaint = "I keep getting double charged on my account every month and nobody is helping me."
    retrieval_result = retrieval_agent.retrieve(test_complaint)
    draft_result = drafting_agent.draft(test_complaint, retrieval_result)
    critique_result = critique_agent.critique(
        complaint_text=test_complaint,
        compliance_flag=False,
        retrieval_result=retrieval_result,
        draft_result=draft_result,
    )

    print(json.dumps(critique_result, indent=2))