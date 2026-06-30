import os
import json
from dotenv import load_dotenv
from google import genai

from agents.config import ROUTER_MODEL
from agents.gemini_client import call_gemini_json

load_dotenv()

ROUTER_PROMPT_TEMPLATE = """You are a consumer complaint classification system.
Classify the complaint below and respond with ONLY a JSON object, no other text.

Complaint:
\"\"\"{complaint_text}\"\"\"

Return JSON in exactly this shape:
{{
  "category": one of ["billing", "product_defect", "shipping_delay", "customer_service", "fraud_or_security", "account_access", "other"],
  "urgency": one of ["low", "medium", "high", "critical"],
  "compliance_flag": true or false (true if the complaint mentions legal action, regulatory bodies, discrimination, safety hazards, or explicit threats),
  "reasoning": a one-sentence explanation of the classification
}}
"""


class RouterAgent:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment. Check your .env file.")
        self.client = genai.Client(api_key=api_key)

    def route(self, complaint_text: str) -> dict:
        prompt = ROUTER_PROMPT_TEMPLATE.format(complaint_text=complaint_text)

        raw_response, model_used = call_gemini_json(
            client=self.client,
            model=ROUTER_MODEL,
            prompt=prompt,
        )

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            raise ValueError(f"Router returned invalid JSON: {raw_response}")

        result["_model_used"] = model_used
        return result


if __name__ == "__main__":
    agent = RouterAgent()

    test_complaint = (
        "I was charged twice for my subscription this month and customer "
        "service has ignored my last three emails. I want a refund immediately."
    )

    result = agent.route(test_complaint)
    print(json.dumps(result, indent=2))