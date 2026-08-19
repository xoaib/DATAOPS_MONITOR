"""
models.py
---------
Pydantic models for FastAPI request and response bodies.
Keeps the API contract clear and easy to understand.
"""

from pydantic import BaseModel
from typing import Optional


# --- Request Models ---

class RunPipelineRequest(BaseModel):
    """Body sent when the user clicks 'Run Pipeline' in the dashboard."""
    pipeline_name: str          # e.g. "Customer Load"
    file_path: str              # e.g. "data/input/customers.csv"


class UpdateIncidentRequest(BaseModel):
    """Body sent when the user updates an incident ticket."""
    status: Optional[str] = None          # OPEN | INVESTIGATING | RESOLVED
    work_notes: Optional[str] = None      # e.g. "Checked source file..."
    resolution: Optional[str] = None      # e.g. "Removed duplicate record..."
    severity: Optional[str] = None        # LOW | MEDIUM | HIGH | CRITICAL


# --- Response Models ---

class PipelineRunResponse(BaseModel):
    run_id: int
    pipeline_name: str
    start_time: str
    end_time: Optional[str]
    records_processed: int
    status: str
    error_message: Optional[str]
    file_path: Optional[str]


class ValidationResultResponse(BaseModel):
    validation_id: int
    run_id: int
    check_name: str
    expected_value: Optional[str]
    actual_value: Optional[str]
    status: str   # PASS | FAIL
    message: Optional[str]
    created_at: str


class IncidentResponse(BaseModel):
    incident_id: str
    run_id: Optional[int]
    pipeline_name: str
    issue: str
    severity: str
    status: str
    created_at: str
    updated_at: str
    resolution: Optional[str]
    work_notes: Optional[str]


class StatsResponse(BaseModel):
    total_runs: int
    successful: int
    failed: int
    warnings: int
    open_incidents: int
    total_records_processed: int
    validation_issues: int
