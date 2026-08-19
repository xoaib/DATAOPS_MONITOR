"""
main.py
-------
FastAPI application entry point.
Defines all API routes for the DataOps Monitor dashboard.

Start the server:
    uvicorn backend.main:app --reload --port 8000
"""

import logging
import os
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db, get_db
from backend.models import (
    RunPipelineRequest,
    UpdateIncidentRequest,
)
from backend import monitor, incidents, reports
from backend.pipeline import run_customer_pipeline, run_order_pipeline

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR  = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),   # also print to console
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="DataOps Monitor API",
    description="Junior Data Engineer Pipeline Monitoring & Validation System",
    version="1.0.0",
)

# Allow the frontend (opened via file:// or a local dev server) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # open for local development; tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
@app.on_event("startup")
def startup():
    logger.info("DataOps Monitor API starting...")
    init_db()
    logger.info("Database ready. API is up.")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "DataOps Monitor"}


# ---------------------------------------------------------------------------
# Stats — dashboard summary cards
# ---------------------------------------------------------------------------
@app.get("/api/stats")
def get_stats():
    """Return aggregate statistics for the dashboard summary cards."""
    return monitor.get_stats()


# ---------------------------------------------------------------------------
# Pipeline Runs
# ---------------------------------------------------------------------------
@app.get("/api/pipeline-runs")
def list_pipeline_runs():
    """Return all pipeline runs, newest first."""
    return monitor.get_all_runs()


@app.get("/api/pipeline-runs/{run_id}")
def get_pipeline_run(run_id: int):
    """Return a single pipeline run by ID."""
    run = monitor.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Pipeline run {run_id} not found.")
    return run


# ---------------------------------------------------------------------------
# Validation Results
# ---------------------------------------------------------------------------
@app.get("/api/validation-results")
def list_validation_results(run_id: int = None):
    """
    Return validation check results.
    Optionally filter by run_id using ?run_id=<id>.
    """
    conn = get_db()
    try:
        if run_id:
            rows = conn.execute(
                "SELECT * FROM validation_results WHERE run_id = ? ORDER BY created_at DESC",
                (run_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM validation_results ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------
@app.get("/api/incidents")
def list_incidents():
    """Return all incidents, newest first."""
    return incidents.get_all_incidents()


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    """Return a single incident by its ID (e.g. INC0001)."""
    inc = incidents.get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")
    return inc


@app.post("/api/incidents/{incident_id}/update")
def update_incident(incident_id: str, body: UpdateIncidentRequest):
    """
    Update an incident ticket.
    Supports changing status, adding work notes, resolution, and severity.
    """
    success = incidents.update_incident(
        incident_id,
        status=body.status,
        work_notes=body.work_notes,
        resolution=body.resolution,
        severity=body.severity,
    )
    if not success:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")
    updated = incidents.get_incident(incident_id)
    return {"message": "Incident updated successfully.", "incident": updated}


# ---------------------------------------------------------------------------
# Run Pipeline
# ---------------------------------------------------------------------------
@app.post("/api/run-pipeline")
def run_pipeline(body: RunPipelineRequest):
    """
    Execute a full ETL pipeline run.

    The pipeline_name determines which pipeline to run:
    - "Customer Load" (or anything containing 'customer') → customers pipeline
    - "Order Load" (or anything else)                     → orders pipeline

    The file_path is the CSV to process (relative to project root).
    """
    logger.info("API: run-pipeline request | name=%s | file=%s",
                body.pipeline_name, body.file_path)

    # Resolve the file path relative to the project root
    project_root = os.path.join(os.path.dirname(__file__), "..")
    abs_file_path = os.path.normpath(os.path.join(project_root, body.file_path))

    if "customer" in body.pipeline_name.lower():
        result = run_customer_pipeline(abs_file_path)
    else:
        result = run_order_pipeline(abs_file_path)

    return result


# ---------------------------------------------------------------------------
# Operational Report
# ---------------------------------------------------------------------------
@app.get("/api/report")
def get_report():
    """Generate and return today's daily operational report."""
    return reports.generate_daily_report()
