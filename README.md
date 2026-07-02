# Multi-Agent Consumer Complaint Resolution System

A production-style 4-agent LLM pipeline that classifies consumer complaints,
retrieves similar past cases via RAG, drafts grounded responses, and runs an
automated compliance check before approving or routing to human review.

Built as a portfolio project targeting Data Scientist / ML Engineer roles.

---

## Architecture
---

## Features

### Core Pipeline
- **Router Agent** — classifies category (7 types), urgency (4 levels), compliance flag
- **Retrieval Agent** — RAG with embedding-based similarity search, embedding cache, graceful no-precedent fallback
- **Drafting Agent** — grounded responses only; conservative ungrounded fallback routes to human review
- **Critique Agent** — independent grounding verification, tone check, compliance acknowledgment check
- **FastAPI Orchestration** — full pipeline via REST API with trace IDs and per-stage JSONL logging

### Pro Features
- **Automated red-teaming** — 6 adversarial test cases (prompt injection, compliance evasion, fabrication bait)
- **Anomaly detection** — flags complaint category spikes from pipeline logs
- **Cost + latency monitoring** — per-stage latency stats, model usage counts
- **Human-in-the-loop feedback** — logs human corrections back into the eval set
- **Async queue worker** — background thread processing with status polling
- **Prompt/model versioning** — every output tagged with prompt version + model used
- **Streamlit dashboard** — live monitoring UI with charts and anomaly alerts

---

## Eval Results (Router Agent, 7-example hand-labeled set)

| Metric | Score |
|---|---|
| Category accuracy | 100% (7/7) |
| Compliance flag accuracy | 85.7% (6/7) |
| Urgency accuracy | 57.1% (4/7) |

Urgency failures were concentrated on over-prediction toward "high" — a documented
LLM safety bias flagged for prompt tuning. Compliance miss was on an unauthorized
account access case where the model did not infer implicit security risk.

Red-team results: 4/6 adversarial cases passed. Documented failure modes:
- Vague complaints ("Everything is wrong. Just fix it.") can slip past fabrication resistance
- Regulatory body mentions in long casual text are sometimes missed by the compliance flag

---

## Tech Stack

- **LLM API:** Google Gemini (free tier) — Flash-Lite, Flash, Embeddings
- **Framework:** FastAPI + Uvicorn
- **RAG:** numpy cosine similarity (no vector DB dependency)
- **Dashboard:** Streamlit
- **Logging:** structured JSONL with trace IDs
- **Language:** Python 3.13

---

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/RajPrajapati05/complaint-resolution-system.git
cd complaint-resolution-system

# 2. Create and activate venv
python -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Gemini API key
# Create a .env file in the project root:
# GEMINI_API_KEY=your_key_here
# Get a free key at https://aistudio.google.com/apikey

# 5. Run the API
uvicorn api.main:app --reload
# Visit http://localhost:8000/docs for interactive API docs

# 6. Run the dashboard
streamlit run dashboard/app.py
# Visit http://localhost:8501
```

---

## Running Evals

```bash
# Basic routing eval (7 hand-labeled examples)
python -m eval.eval_runner

# Red-team adversarial eval (6 cases)
python -m eval.red_team_runner

# Anomaly detection report
python -m agents.anomaly_detector

# Latency + cost monitoring report
python -m agents.monitoring
```

---

## Interview Talking Points

**On architecture decisions:**
- Chose numpy cosine similarity over FAISS — justified at this dataset scale,
  and documents the tradeoff explicitly. FAISS swap-in is a natural scaling path.
- Critique Agent independently re-reads precedents rather than trusting the
  Drafting Agent's self-report — second set of eyes, not a rubber stamp.
- Conservative fallback design: no precedent = acknowledgment-only draft,
  mandatory human review. System refuses to fabricate resolutions.

**On the free-tier constraint:**
- Spread agents across different Gemini models to avoid shared daily quota.
- Built retry/backoff with 429 handling and fallback model logic from day one.
- When Google restricted Pro models to paid tier mid-project, redesigned
  model allocation without changing the pipeline architecture.

**On eval methodology:**
- Hand-labeled eval set, not auto-generated — results are credible.
- 100% category accuracy; urgency over-prediction documented honestly
  rather than tuned away to inflate the number.
- Red-team revealed two real failure modes — documented and left in,
  because honest failure analysis is more valuable than a perfect score.

**On production readiness signals:**
- Structured JSONL logging with trace IDs for every pipeline run
- Prompt + model versioning so behavior changes are auditable
- Human feedback loop feeds corrections back into the eval set
- Async queue worker for non-blocking processing under volume

