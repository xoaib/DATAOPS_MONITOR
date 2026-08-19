"""
reports.py
----------
Generates the daily operational pipeline report.
"""

import logging
from datetime import datetime, timezone
from backend.database import get_db

logger = logging.getLogger(__name__)


def generate_daily_report() -> dict:
    """
    Build today's operational report.

    Returns a dict containing both raw data and a formatted text block
    that can be displayed directly in the dashboard.
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_date = datetime.now(timezone.utc).strftime("%B %d, %Y")

    conn = get_db()
    try:
        # --- Pipeline run stats for today ---
        run_row = conn.execute(
            """
            SELECT
                COUNT(*)                                             AS total_runs,
                SUM(CASE WHEN status = 'SUCCESS'  THEN 1 ELSE 0 END) AS successful,
                SUM(CASE WHEN status = 'FAILED'   THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN status = 'WARNING'  THEN 1 ELSE 0 END) AS warnings,
                COALESCE(SUM(records_processed), 0)                  AS total_records
            FROM pipeline_runs
            WHERE DATE(start_time) = ?
            """,
            (today,),
        ).fetchone()

        total_runs    = run_row["total_runs"]    or 0
        successful    = run_row["successful"]    or 0
        failed        = run_row["failed"]        or 0
        warnings      = run_row["warnings"]      or 0
        total_records = run_row["total_records"] or 0

        # --- Validation issue count for today ---
        val_row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM validation_results vr
            JOIN pipeline_runs pr ON vr.run_id = pr.run_id
            WHERE vr.status = 'FAIL'
              AND DATE(pr.start_time) = ?
            """,
            (today,),
        ).fetchone()
        validation_issues = val_row["cnt"] or 0

        # --- Incident counts ---
        open_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM incidents WHERE status IN ('OPEN', 'INVESTIGATING')"
        ).fetchone()
        open_incidents = open_row["cnt"] or 0

        resolved_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM incidents WHERE status = 'RESOLVED'"
        ).fetchone()
        resolved_incidents = resolved_row["cnt"] or 0

        # --- Pipelines that ran today (detail) ---
        pipeline_details = conn.execute(
            """
            SELECT pipeline_name, start_time, end_time, records_processed, status, error_message
            FROM pipeline_runs
            WHERE DATE(start_time) = ?
            ORDER BY start_time ASC
            """,
            (today,),
        ).fetchall()

    finally:
        conn.close()

    # Build pipeline detail lines
    detail_lines = []
    for p in pipeline_details:
        end = p["end_time"] or "In Progress"
        detail_lines.append(
            f"  {p['pipeline_name']:<25} | {p['status']:<8} | Records: {p['records_processed']:>6}"
        )
        if p["error_message"]:
            detail_lines.append(f"    Error: {p['error_message'][:80]}")

    detail_block = "\n".join(detail_lines) if detail_lines else "  No pipelines ran today."

    # Build the formatted text report
    text_report = f"""
{'=' * 48}
  DAILY DATA PIPELINE REPORT
  DataOps Monitor
{'=' * 48}

  Date: {report_date}

  PIPELINE SUMMARY
  ----------------
  Total Runs:           {total_runs:>6}
  Successful:           {successful:>6}
  Failed:               {failed:>6}
  Warnings:             {warnings:>6}

  Records Processed:    {total_records:>6,}

  VALIDATION
  ----------
  Validation Issues:    {validation_issues:>6}

  INCIDENTS
  ---------
  Open Incidents:       {open_incidents:>6}
  Resolved Incidents:   {resolved_incidents:>6}

  PIPELINE DETAILS (TODAY)
  ------------------------
{detail_block}

{'=' * 48}
  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC
{'=' * 48}
""".strip()

    logger.info("Daily report generated for %s", today)

    return {
        "date": today,
        "total_runs": total_runs,
        "successful": successful,
        "failed": failed,
        "warnings": warnings,
        "total_records_processed": total_records,
        "validation_issues": validation_issues,
        "open_incidents": open_incidents,
        "resolved_incidents": resolved_incidents,
        "text_report": text_report,
    }
