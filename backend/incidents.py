"""
incidents.py
------------
ServiceNow-style incident management.
Creates and updates incident tickets in the database.
"""

from typing import Optional

import logging
from datetime import datetime, timezone
from backend.database import get_db

logger = logging.getLogger(__name__)


def _next_incident_id(conn) -> str:
    """Generate the next INC-style ID, e.g. INC0001, INC0002."""
    row = conn.execute("SELECT COUNT(*) AS cnt FROM incidents").fetchone()
    count = row["cnt"] + 1
    return f"INC{count:04d}"


def create_incident(
    run_id: int,
    pipeline_name: str,
    issue: str,
    severity: str = "MEDIUM",
) -> str:
    """
    Create a new incident ticket when a pipeline fails.

    Args:
        run_id: The failed pipeline run ID.
        pipeline_name: Name of the failed pipeline.
        issue: Short description of the problem.
        severity: LOW | MEDIUM | HIGH | CRITICAL

    Returns:
        The generated incident_id string (e.g. "INC0001").
    """
    conn = get_db()
    try:
        incident_id = _next_incident_id(conn)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        conn.execute(
            """
            INSERT INTO incidents (incident_id, run_id, pipeline_name, issue, severity, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?)
            """,
            (incident_id, run_id, pipeline_name, issue, severity, now, now),
        )
        conn.commit()
        logger.info(
            "Incident created — %s | Pipeline: %s | Issue: %s | Severity: %s",
            incident_id, pipeline_name, issue, severity,
        )
        return incident_id
    finally:
        conn.close()


def update_incident(  # noqa: E302
    incident_id: str,
    status: str = None,
    work_notes: str = None,
    resolution: str = None,
    severity: str = None,
) -> bool:
    """
    Update an existing incident.

    Supports:
    - Changing status (OPEN → INVESTIGATING → RESOLVED)
    - Appending work notes
    - Adding a resolution
    - Changing severity

    Returns:
        True if updated, False if incident not found.
    """
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
        ).fetchone()

        if not row:
            logger.warning("Incident not found: %s", incident_id)
            return False

        existing = dict(row)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        # Append new work notes to existing ones
        updated_notes = existing["work_notes"] or ""
        if work_notes:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            updated_notes = (
                f"{updated_notes}\n[{timestamp}] {work_notes}".strip()
            )

        conn.execute(
            """
            UPDATE incidents
            SET
                status     = COALESCE(?, status),
                severity   = COALESCE(?, severity),
                resolution = COALESCE(?, resolution),
                work_notes = ?,
                updated_at = ?
            WHERE incident_id = ?
            """,
            (status, severity, resolution, updated_notes or None, now, incident_id),
        )
        conn.commit()
        logger.info(
            "Incident updated — %s | New status: %s",
            incident_id, status or existing["status"],
        )
        return True
    finally:
        conn.close()


def get_all_incidents() -> list:
    """Return all incidents ordered by creation date (newest first)."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_incident(incident_id: str) -> Optional[dict]:
    """Return a single incident by its ID."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
