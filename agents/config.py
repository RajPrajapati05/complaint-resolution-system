# agents/config.py
# Central place for model assignments per agent.
# Each agent uses a different model to spread load across separate daily quotas.
# NOTE: As of the free tier as of mid-2026, only Flash and Flash-Lite models
# are available for free - Pro models require a paid billing account.

ROUTER_MODEL = "gemini-2.5-flash-lite"
RETRIEVAL_EMBEDDING_MODEL = "gemini-embedding-001"
DRAFTING_MODEL = "gemini-2.5-flash"
CRITIQUE_MODEL = "gemini-2.5-flash"

# Fallback model used if the primary model returns a 503 (overloaded)
FALLBACK_MODEL = "gemini-2.5-flash-lite"