import time
from google import genai
from google.genai import types
from agents.config import FALLBACK_MODEL


def call_gemini_json(client, model, prompt, max_retries=3):
    """
    Calls Gemini with a prompt expecting a clean JSON response.
    Disables 'thinking' to avoid truncated structured output.
    Retries with exponential backoff on 503 (overloaded) errors,
    and waits 15s on 429 rate-limit errors before retrying.
    Falls back to FALLBACK_MODEL if the primary model keeps failing.
    """
    models_to_try = [model, FALLBACK_MODEL]

    for attempt_model in models_to_try:
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=attempt_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                        response_mime_type="application/json",
                    ),
                )
                return response.text, attempt_model
            except Exception as e:
                error_str = str(e)
                is_overloaded = "503" in error_str or "overloaded" in error_str.lower()
                is_rate_limited = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
                is_last_attempt = attempt == max_retries - 1
                should_retry = (is_overloaded or is_rate_limited) and not is_last_attempt

                if should_retry:
                    wait_time = 15 if is_rate_limited else 2 ** attempt
                    print(f"  [retry] {attempt_model} rate-limited/overloaded, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                elif is_overloaded or is_rate_limited:
                    print(f"  [fallback] {attempt_model} still failing, trying fallback model...")
                    break
                else:
                    raise

    raise RuntimeError("All models failed after retries and fallback.")