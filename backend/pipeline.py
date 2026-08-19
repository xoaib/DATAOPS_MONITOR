"""
pipeline.py
-----------
Orchestrates the full ETL pipeline run.

Flow:
  1. Create pipeline run record (STARTED)
  2. Extract CSV
  3. Run validation checks
  4. Transform data
  5. Load into database (with transaction)
  6. Source-to-target reconciliation
  7. Update pipeline run (SUCCESS / FAILED)
  8. Create incident if FAILED
"""

import logging
import os
from datetime import datetime, timezone

import pandas as pd

from backend import extract, validate, transform, monitor, incidents
from backend.database import get_db

logger = logging.getLogger(__name__)

# Expected columns for each pipeline type
CUSTOMER_COLUMNS = ["customer_id", "name", "email", "city"]
ORDER_COLUMNS    = ["order_id", "customer_id", "order_date", "amount", "status"]

# Severity mapping based on failure type
SEVERITY_MAP = {
    "FileNotFoundError": "HIGH",
    "empty":             "MEDIUM",
    "missing_column":    "HIGH",
    "duplicate":         "MEDIUM",
    "null":              "MEDIUM",
    "invalid":           "MEDIUM",
    "db_load":           "HIGH",
    "reconciliation":    "MEDIUM",
    "unknown":           "HIGH",
}


def _save_validation_results(run_id: int, results: list):
    """Write a list of validation result dicts into validation_results table."""
    conn = get_db()
    try:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        for r in results:
            conn.execute(
                """
                INSERT INTO validation_results
                    (run_id, check_name, expected_value, actual_value, status, message, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    r["check_name"],
                    r["expected_value"],
                    r["actual_value"],
                    r["status"],
                    r["message"],
                    now,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _load_customers(df: pd.DataFrame):
    """Insert customer records into the database. Returns count loaded."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM customers")   # clear before reload
        loaded = 0
        for _, row in df.iterrows():
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO customers (customer_id, name, email, city) VALUES (?, ?, ?, ?)",
                    (
                        int(row["customer_id"]) if pd.notna(row["customer_id"]) else None,
                        str(row["name"]) if pd.notna(row["name"]) else None,
                        str(row["email"]) if pd.notna(row["email"]) else None,
                        str(row["city"]) if pd.notna(row["city"]) else None,
                    ),
                )
                loaded += 1
            except Exception as e:
                logger.warning("Skipping row due to error: %s", e)
        conn.commit()
        logger.info("Loaded %d customer records.", loaded)
        return loaded
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _load_orders(df: pd.DataFrame):
    """Insert order records into the database. Returns count loaded."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM orders")      # clear before reload
        loaded = 0
        for _, row in df.iterrows():
            try:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO orders
                        (order_id, customer_id, order_date, amount, status)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        int(row["order_id"])     if pd.notna(row.get("order_id"))     else None,
                        int(row["customer_id"])  if pd.notna(row.get("customer_id"))  else None,
                        str(row["order_date"])   if pd.notna(row.get("order_date"))   else None,
                        float(row["amount"])     if pd.notna(row.get("amount"))       else None,
                        str(row["status"])       if pd.notna(row.get("status"))       else None,
                    ),
                )
                loaded += 1
            except Exception as e:
                logger.warning("Skipping order row due to error: %s", e)
        conn.commit()
        logger.info("Loaded %d order records.", loaded)
        return loaded
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _get_target_count(pipeline_name: str) -> int:
    """Return the current row count in the target table."""
    conn = get_db()
    try:
        if "customer" in pipeline_name.lower():
            table = "customers"
        else:
            table = "orders"
        row = conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
        return row["cnt"]
    finally:
        conn.close()


def run_customer_pipeline(file_path: str) -> dict:
    """Run the full ETL pipeline for customers.csv."""
    return _run_pipeline(
        pipeline_name="Customer Load",
        file_path=file_path,
        expected_columns=CUSTOMER_COLUMNS,
        id_column="customer_id",
        required_fields=["customer_id", "name", "email"],
        transform_fn=transform.transform_customers,
        load_fn=_load_customers,
        has_order_checks=False,
    )


def run_order_pipeline(file_path: str) -> dict:
    """Run the full ETL pipeline for orders.csv."""
    return _run_pipeline(
        pipeline_name="Order Load",
        file_path=file_path,
        expected_columns=ORDER_COLUMNS,
        id_column="order_id",
        required_fields=["order_id", "customer_id", "amount", "status"],
        transform_fn=transform.transform_orders,
        load_fn=_load_orders,
        has_order_checks=True,
    )


def _run_pipeline(
    pipeline_name: str,
    file_path: str,
    expected_columns: list,
    id_column: str,
    required_fields: list,
    transform_fn,
    load_fn,
    has_order_checks: bool,
) -> dict:
    """
    Generic pipeline runner.

    Returns a result dict with:
        run_id, status, records_processed, error_message,
        validation_results, incident_id
    """
    logger.info("=" * 60)
    logger.info("PIPELINE STARTED: %s | File: %s", pipeline_name, file_path)
    logger.info("=" * 60)

    # --- Step 1: Create run record ---
    run_id = monitor.create_run(pipeline_name, file_path)
    validation_results = []
    incident_id = None
    records_processed = 0
    failure_reason = "unknown"

    try:
        # --- Step 2: Extract ---
        logger.info("Step 2: Extracting CSV...")
        df_raw = extract.extract_csv(file_path, expected_columns)
        records_processed = len(df_raw)

        # --- Step 3: Validate ---
        logger.info("Step 3: Running data validation checks...")

        # Check 1: Required columns (already done in extract, but record it)
        validation_results.append(
            validate.check_required_columns(df_raw, expected_columns)
        )

        # Check 2: Empty file
        validation_results.append(validate.check_empty_file(df_raw))

        # Check 3: NULL values
        validation_results.append(validate.check_nulls(df_raw, required_fields))

        # Check 4: Duplicates
        validation_results.append(validate.check_duplicates(df_raw, id_column))

        # Check 5: Invalid values (orders only)
        if has_order_checks:
            validation_results.append(validate.check_invalid_values(df_raw))

        # Stop pipeline if any critical check failed
        failed_checks = [r for r in validation_results if r["status"] == "FAIL"]
        if failed_checks:
            issues = "; ".join([r["message"] for r in failed_checks])
            failure_reason = "duplicate" if "uplicate" in issues else \
                             "null"      if "null"  in issues.lower() else \
                             "invalid"   if "invalid" in issues.lower() else "unknown"

            logger.error("Validation FAILED: %s", issues)
            _save_validation_results(run_id, validation_results)
            monitor.complete_run(run_id, records_processed, "FAILED", issues)
            incident_id = incidents.create_incident(run_id, pipeline_name, issues,
                                                     SEVERITY_MAP.get(failure_reason, "MEDIUM"))
            return {
                "run_id": run_id,
                "status": "FAILED",
                "records_processed": records_processed,
                "error_message": issues,
                "validation_results": validation_results,
                "incident_id": incident_id,
            }

        logger.info("All validation checks passed.")

        # --- Step 4: Transform ---
        logger.info("Step 4: Transforming data...")
        df_clean = transform_fn(df_raw)

        # --- Step 5: Load ---
        logger.info("Step 5: Loading data into database...")
        loaded_count = load_fn(df_clean)

        # --- Step 6: Reconciliation ---
        logger.info("Step 6: Running source-to-target reconciliation...")
        target_count = _get_target_count(pipeline_name)
        recon_result = validate.check_reconciliation(loaded_count, target_count, pipeline_name)
        validation_results.append(recon_result)

        _save_validation_results(run_id, validation_results)

        if recon_result["status"] == "FAIL":
            failure_reason = "reconciliation"
            msg = recon_result["message"]
            logger.warning("Reconciliation FAILED: %s", msg)
            monitor.complete_run(run_id, loaded_count, "WARNING", msg)
            incident_id = incidents.create_incident(run_id, pipeline_name, msg,
                                                     SEVERITY_MAP["reconciliation"])
            return {
                "run_id": run_id,
                "status": "WARNING",
                "records_processed": loaded_count,
                "error_message": msg,
                "validation_results": validation_results,
                "incident_id": incident_id,
            }

        # --- Step 7: SUCCESS ---
        monitor.complete_run(run_id, loaded_count, "SUCCESS")
        logger.info("PIPELINE COMPLETED SUCCESSFULLY — %s | Records: %d", pipeline_name, loaded_count)

        return {
            "run_id": run_id,
            "status": "SUCCESS",
            "records_processed": loaded_count,
            "error_message": None,
            "validation_results": validation_results,
            "incident_id": None,
        }

    except FileNotFoundError as e:
        msg = f"Input file not found: {e}"
        logger.error(msg)
        _save_validation_results(run_id, validation_results)
        monitor.complete_run(run_id, 0, "FAILED", msg)
        incident_id = incidents.create_incident(run_id, pipeline_name, msg, SEVERITY_MAP["FileNotFoundError"])
        return {"run_id": run_id, "status": "FAILED", "records_processed": 0,
                "error_message": msg, "validation_results": validation_results, "incident_id": incident_id}

    except ValueError as e:
        msg = str(e)
        logger.error("Pipeline FAILED (ValueError): %s", msg)
        failure_reason = "empty" if "zero records" in msg else \
                         "missing_column" if "Missing required" in msg else "unknown"
        _save_validation_results(run_id, validation_results)
        monitor.complete_run(run_id, records_processed, "FAILED", msg)
        incident_id = incidents.create_incident(run_id, pipeline_name, msg,
                                                 SEVERITY_MAP.get(failure_reason, "MEDIUM"))
        return {"run_id": run_id, "status": "FAILED", "records_processed": records_processed,
                "error_message": msg, "validation_results": validation_results, "incident_id": incident_id}

    except Exception as e:
        msg = f"Unexpected error during pipeline execution: {e}"
        logger.error(msg, exc_info=True)
        _save_validation_results(run_id, validation_results)
        monitor.complete_run(run_id, records_processed, "FAILED", msg)
        incident_id = incidents.create_incident(run_id, pipeline_name, msg, SEVERITY_MAP["db_load"])
        return {"run_id": run_id, "status": "FAILED", "records_processed": records_processed,
                "error_message": msg, "validation_results": validation_results, "incident_id": incident_id}
