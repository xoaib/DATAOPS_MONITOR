"""
monitor.py
----------
Pipeline monitoring helpers.
Creates and updates records in the pipeline_runs table.
"""

from typing import Optional, List

import logging
from datetime import datetime, timezone
from backend.database import get_db

logger = logging.getLogger(__name__)


def create_run(pipeline_name: str, file_path: str = None) -> int:
    """
    Insert a new STARTED pipeline run record.

    Args:
        pipeline_name: Human-readable name, e.g. "Customer Load".
        file_path: The input file being processed.

    Returns:
        The auto-generated run_id.
    """
    start_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO pipeline_runs (pipeline_name, start_time, status, file_path)
            VALUES (?, ?, 'STARTED', ?)
            """,
            (pipeline_name, start_time, file_path),
        )
        conn.commit()
        run_id = cursor.lastrowid
        logger.info("Pipeline run created — run_id: %d, name: %s", run_id, pipeline_name)
        return run_id
    finally:
        conn.close()


def complete_run(run_id: int, records_processed: int, status: str, error_message: str = None):
    """
    Update an existing pipeline run with its final status.

    Args:
        run_id: The pipeline run to update.
        records_processed: How many records were handled.
        status: SUCCESS | FAILED | WARNING
        error_message: Error detail if status is FAILED.
    """
    end_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    try:
        conn.execute(
            """
            UPDATE pipeline_runs
            SET end_time = ?, records_processed = ?, status = ?, error_message = ?
            WHERE run_id = ?
            """,
            (end_time, records_processed, status, error_message, run_id),
        )
        conn.commit()
        logger.info(
            "Pipeline run updated — run_id: %d, status: %s, records: %d",
            run_id, status, records_processed,
        )
    finally:
        conn.close()


def get_all_runs() -> list:
    """Return all pipeline runs ordered by start time (newest first)."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY start_time DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_run(run_id: int) -> Optional[dict]:
    """Return a single pipeline run by its ID."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_stats() -> dict:
    """
    Return dashboard summary statistics:
    - Total runs
    - Successful / failed / warning counts
    - Total records processed
    - Open incidents
    - Validation issues (FAIL results)
    """
    conn = get_db()
    try:
        run_stats = conn.execute(
            """
            SELECT
                COUNT(*)                                             AS total_runs,
                SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END)  AS successful,
                SUM(CASE WHEN status='FAILED'  THEN 1 ELSE 0 END)  AS failed,
                SUM(CASE WHEN status='WARNING' THEN 1 ELSE 0 END)  AS warnings,
                COALESCE(SUM(records_processed), 0)                AS total_records_processed
            FROM pipeline_runs
            """
        ).fetchone()

        open_incidents = conn.execute(
            "SELECT COUNT(*) AS cnt FROM incidents WHERE status IN ('OPEN', 'INVESTIGATING')"
        ).fetchone()["cnt"]

        validation_issues = conn.execute(
            "SELECT COUNT(*) AS cnt FROM validation_results WHERE status = 'FAIL'"
        ).fetchone()["cnt"]

        return {
            "total_runs": run_stats["total_runs"] or 0,
            "successful": run_stats["successful"] or 0,
            "failed": run_stats["failed"] or 0,
            "warnings": run_stats["warnings"] or 0,
            "total_records_processed": run_stats["total_records_processed"] or 0,
            "open_incidents": open_incidents,
            "validation_issues": validation_issues,
        }
    finally:
        conn.close()
