import os
import json
from dotenv import load_dotenv
from google import genai

from agents.config import DRAFTING_MODEL
from agents.gemini_client import call_gemini_json

load_dotenv()

GROUNDED_PROMPT_TEMPLATE = """You are a customer support response drafter for a consumer complaints team.

You must draft a response using ONLY the precedent cases provided below as grounding.
Do NOT invent any refund amounts, policy details, timelines, or legal/compliance promises
that are not directly supported by the precedent resolutions shown.
If the precedents don't fully cover something, acknowledge it generally rather than inventing specifics.

Customer complaint:
\"\"\"{complaint_text}\"\"\"

Precedent cases (past similar complaints and how they were resolved):
{precedent_block}

Respond with ONLY a JSON object in exactly this shape:
{{
  "draft_response": "the customer-facing response text, professional and empathetic",
  "precedent_ids_used": ["list of precedent IDs actually referenced or relied upon, e.g. C001"],
  "grounded": true
}}
"""

UNGROUNDED_TEMPLATE = {
    "draft_response": (
        "Thank you for reaching out and sharing the details of your concern. "
        "We want to make sure this is handled correctly, so we're routing your "
        "case to a member of our team for personal review. We'll follow up with "
        "next steps as soon as possible."
    ),
    "precedent_ids_used": [],
    "grounded": False,
}


class DraftingAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")
        self.client = genai.Client(api_key=api_key)

    def draft(self, complaint_text: str, retrieval_result: dict) -> dict:
        precedents = retrieval_result.get("precedents", [])

        if not precedents:
            result = dict(UNGROUNDED_TEMPLATE)
            result["requires_human_review"] = True
            result["review_reason"] = "no_precedent_found"
            return result

        precedent_block = "\n".join(
            f"- [{p['id']}] Complaint: \"{p['complaint_text']}\" | "
            f"Resolution: \"{p['resolution']}\" | Similarity: {p['similarity_score']}"
            for p in precedents
        )

        prompt = GROUNDED_PROMPT_TEMPLATE.format(
            complaint_text=complaint_text,
            precedent_block=precedent_block,
        )

        raw_response, model_used = call_gemini_json(
            client=self.client,
            model=DRAFTING_MODEL,
            prompt=prompt,
        )

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            raise ValueError(f"Drafting agent returned invalid JSON: {raw_response}")

        # Validate the model actually cited real precedent IDs, not invented ones
        valid_ids = {p["id"] for p in precedents}
        cited_ids = set(result.get("precedent_ids_used", []))
        invalid_ids = cited_ids - valid_ids
        if invalid_ids:
            result["_warning"] = f"Model cited unknown precedent IDs: {invalid_ids}"
            result["precedent_ids_used"] = list(cited_ids & valid_ids)

        result["requires_human_review"] = len(result.get("precedent_ids_used", [])) == 0
        result["review_reason"] = (
            "model_did_not_cite_precedent" if result["requires_human_review"] else None
        )
        result["_model_used"] = model_used
        return result


if __name__ == "__main__":
    from agents.retrieval_agent import RetrievalAgent

    retrieval_agent = RetrievalAgent()
    drafting_agent = DraftingAgent()

    test_complaint = "I keep getting double charged on my account every month and nobody is helping me."
    retrieval_result = retrieval_agent.retrieve(test_complaint)

    draft_result = drafting_agent.draft(test_complaint, retrieval_result)
    print(json.dumps(draft_result, indent=2))