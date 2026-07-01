import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.orchestrator import Orchestrator

app = FastAPI(
    title="Consumer Complaint Resolution System",
    description="A 4-agent LLM pipeline that classifies, retrieves, drafts, and critiques consumer complaint responses.",
    version="1.0.0",
)

orchestrator = Orchestrator()


class ComplaintRequest(BaseModel):
    complaint_text: str


class HealthResponse(BaseModel):
    status: str
    message: str


@app.get("/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "message": "Complaint resolution system is running."}


@app.post("/complaints")
def process_complaint(request: ComplaintRequest):
    if not request.complaint_text.strip():
        raise HTTPException(status_code=400, detail="complaint_text cannot be empty.")
    try:
        result = orchestrator.process_complaint(request.complaint_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        