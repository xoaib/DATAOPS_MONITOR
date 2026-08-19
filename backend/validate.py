"""
validate.py
-----------
Data validation checks for the incoming CSV data.
Each check returns a dict describing the result (PASS/FAIL).
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

# Allowed order statuses
ALLOWED_STATUSES = {"PENDING", "COMPLETED", "CANCELLED"}


def _make_result(check_name: str, expected: str, actual: str, status: str, message: str) -> dict:
    """Helper to build a consistent validation result dict."""
    return {
        "check_name": check_name,
        "expected_value": expected,
        "actual_value": actual,
        "status": status,     # PASS or FAIL
        "message": message,
    }


# ---------------------------------------------------------------
# Check 1: Required columns present
# ---------------------------------------------------------------
def check_required_columns(df: pd.DataFrame, expected_columns: list) -> dict:
    """Verify all expected columns exist in the DataFrame."""
    missing = [col for col in expected_columns if col not in df.columns]

    if missing:
        msg = f"Missing columns: {missing}"
        logger.warning("Required Column Check — FAIL: %s", msg)
        return _make_result(
            "Required Column Check",
            f"Columns: {expected_columns}",
            f"Actual columns: {list(df.columns)}",
            "FAIL",
            msg,
        )

    logger.info("Required Column Check — PASS")
    return _make_result(
        "Required Column Check",
        f"Columns: {expected_columns}",
        f"Columns: {list(df.columns)}",
        "PASS",
        "All required columns are present.",
    )


# ---------------------------------------------------------------
# Check 2: Empty file
# ---------------------------------------------------------------
def check_empty_file(df: pd.DataFrame) -> dict:
    """Check that the DataFrame has at least one data row."""
    if df.empty or len(df) == 0:
        msg = "Input file contains zero records."
        logger.warning("Empty File Check — FAIL: %s", msg)
        return _make_result("Empty File Check", ">= 1 record", "0 records", "FAIL", msg)

    logger.info("Empty File Check — PASS (%d records)", len(df))
    return _make_result(
        "Empty File Check", ">= 1 record", f"{len(df)} records", "PASS",
        f"File contains {len(df)} records."
    )


# ---------------------------------------------------------------
# Check 3: NULL values in required fields
# ---------------------------------------------------------------
def check_nulls(df: pd.DataFrame, required_fields: list) -> dict:
    """Check for NULL/empty values in required fields."""
    null_issues = []

    for field in required_fields:
        if field not in df.columns:
            continue
        # Find rows where the field is null or blank
        null_mask = df[field].isnull() | (df[field].astype(str).str.strip() == "")
        null_rows = df[null_mask]
        if not null_rows.empty:
            null_issues.append(f"'{field}' has {len(null_rows)} null/empty value(s)")

    if null_issues:
        msg = "; ".join(null_issues)
        logger.warning("NULL Check — FAIL: %s", msg)
        return _make_result(
            "NULL Check",
            "No nulls in required fields",
            msg,
            "FAIL",
            msg,
        )

    logger.info("NULL Check — PASS")
    return _make_result(
        "NULL Check",
        "No nulls in required fields",
        "No nulls found",
        "PASS",
        "No missing values in required fields.",
    )


# ---------------------------------------------------------------
# Check 4: Duplicate IDs
# ---------------------------------------------------------------
def check_duplicates(df: pd.DataFrame, id_column: str) -> dict:
    """Check for duplicate values in the ID column."""
    if id_column not in df.columns:
        return _make_result(
            "Duplicate Check",
            f"No duplicates in {id_column}",
            "Column not found",
            "FAIL",
            f"ID column '{id_column}' not found in data.",
        )

    duplicated = df[df.duplicated(subset=[id_column], keep=False)]

    if not duplicated.empty:
        dup_ids = duplicated[id_column].unique().tolist()
        msg = f"Duplicate {id_column}(s) found: {dup_ids}"
        logger.warning("Duplicate Check — FAIL: %s", msg)
        return _make_result(
            "Duplicate Check",
            f"No duplicates in {id_column}",
            f"{len(duplicated)} duplicate rows",
            "FAIL",
            msg,
        )

    logger.info("Duplicate Check — PASS")
    return _make_result(
        "Duplicate Check",
        f"No duplicates in {id_column}",
        "No duplicates",
        "PASS",
        f"No duplicate {id_column} values found.",
    )


# ---------------------------------------------------------------
# Check 5: Invalid values (orders-specific)
# ---------------------------------------------------------------
def check_invalid_values(df: pd.DataFrame) -> dict:
    """
    Check for invalid order amounts and statuses.
    - amount must be >= 0 and numeric
    - status must be in ALLOWED_STATUSES
    """
    issues = []

    # Check amount column
    if "amount" in df.columns:
        # Try converting to numeric; non-numeric becomes NaN
        amounts = pd.to_numeric(df["amount"], errors="coerce")
        non_numeric = df[amounts.isna()]
        negative = df[amounts < 0]

        if not non_numeric.empty:
            issues.append(f"{len(non_numeric)} row(s) have non-numeric amount")
        if not negative.empty:
            issues.append(f"{len(negative)} row(s) have negative amount")

    # Check status column
    if "status" in df.columns:
        invalid_statuses = df[~df["status"].str.upper().isin(ALLOWED_STATUSES)]
        if not invalid_statuses.empty:
            bad = invalid_statuses["status"].unique().tolist()
            issues.append(f"Invalid status value(s): {bad}. Allowed: {list(ALLOWED_STATUSES)}")

    if issues:
        msg = "; ".join(issues)
        logger.warning("Invalid Value Check — FAIL: %s", msg)
        return _make_result(
            "Invalid Value Check",
            "amount >= 0, status in {PENDING, COMPLETED, CANCELLED}",
            msg,
            "FAIL",
            msg,
        )

    logger.info("Invalid Value Check — PASS")
    return _make_result(
        "Invalid Value Check",
        "amount >= 0, status in {PENDING, COMPLETED, CANCELLED}",
        "All values valid",
        "PASS",
        "All amounts and statuses are valid.",
    )


# ---------------------------------------------------------------
# Check 6: Source-to-target reconciliation
# ---------------------------------------------------------------
def check_reconciliation(source_count: int, target_count: int, pipeline_name: str) -> dict:
    """
    Compare the number of source records with the number loaded into the DB.
    A mismatch means data was lost during loading.
    """
    difference = source_count - target_count

    if difference != 0:
        msg = f"Mismatch: {abs(difference)} record(s) {'lost' if difference > 0 else 'extra'} in target"
        logger.warning("Reconciliation — FAIL: %s", msg)
        return _make_result(
            "Source-to-Target Reconciliation",
            f"Source: {source_count}",
            f"Target: {target_count} (diff: {difference})",
            "FAIL",
            msg,
        )

    logger.info("Reconciliation — PASS (%d records match)", source_count)
    return _make_result(
        "Source-to-Target Reconciliation",
        f"Source: {source_count}",
        f"Target: {target_count}",
        "PASS",
        f"Source and target counts match: {source_count} records.",
    )
