from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from .models import UrlCreate, ScenarioRequest, ApprovalRequest
from .store import SQLiteStore
from .url_service import UrlService
from .orchestrator import Orchestrator

app = FastAPI(title="Agentic URL Shortener", version="1.0.0")
store = SQLiteStore()
urls = UrlService(store)
orchestrator = Orchestrator(store)

@app.get("/health")
def health(): return {"status": "UP"}

@app.post("/api/v1/shorten")
def shorten(req: UrlCreate): return urls.shorten(req)

@app.get("/api/v1/analytics/{code}")
def analytics(code: str): return urls.analytics(code)

@app.get("/{code}")
def redirect(code: str): return RedirectResponse(urls.resolve(code), status_code=307)

@app.post("/api/v1/agent/runs")
def start_run(req: ScenarioRequest): return orchestrator.start(req.scenario, req.requirement, req.auto_approve_low_risk)

@app.get("/api/v1/agent/runs/{run_id}")
def run_status(run_id: str):
    if run_id not in orchestrator.runs: raise HTTPException(404, "Run not found")
    return orchestrator.snapshot(run_id)

@app.post("/api/v1/agent/runs/{run_id}/approve")
def approve(run_id: str, req: ApprovalRequest):
    if run_id not in orchestrator.runs: raise HTTPException(404, "Run not found")
    return orchestrator.approve(run_id, req.approved, req.comment)

@app.post("/api/v1/agent/runs/{run_id}/rollback")
def rollback(run_id: str):
    if run_id not in orchestrator.runs: raise HTTPException(404, "Run not found")
    return orchestrator.rollback(run_id)

@app.post("/api/v1/agent/runs/{run_id}/replan")
def replan(run_id: str, req: ScenarioRequest):
    if run_id not in orchestrator.runs: raise HTTPException(404, "Run not found")
    return orchestrator.replan(run_id, req.requirement)

@app.get("/api/v1/agent/runs/{run_id}/audit")
def audit(run_id: str):
    if run_id not in orchestrator.runs: raise HTTPException(404, "Run not found")
    return orchestrator.audit(run_id)
