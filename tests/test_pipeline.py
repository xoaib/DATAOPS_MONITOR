"""
test_pipeline.py
----------------
Basic unit tests for the DataOps Monitor ETL pipeline.

Run with:
    pytest tests/test_pipeline.py -v

These tests validate core pipeline logic:
- CSV extraction
- Data validation checks
- Pipeline execution (success and failure paths)
- Incident creation
- Incident update
"""

import os
import sys
import pytest
import pandas as pd

# Make sure the project root is on the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend import extract, validate, incidents
from backend.database import init_db, get_db

# ============================================================
# Setup — use a temporary in-memory test database
# ============================================================

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    """
    Patch DB_PATH to a temporary file so tests don't pollute the real database.
    """
    test_db = str(tmp_path / "test_dataops.db")
    monkeypatch.setattr("backend.database.DB_PATH", test_db)
    monkeypatch.setattr("backend.monitor.get_db", lambda: __import__("backend.database", fromlist=["get_db"]).get_db())
    monkeypatch.setattr("backend.incidents.get_db", lambda: __import__("backend.database", fromlist=["get_db"]).get_db())
    init_db()
    yield


# ============================================================
# EXTRACTION TESTS
# ============================================================

class TestExtraction:

    def test_valid_csv(self, tmp_path):
        """Valid CSV with all required columns should load successfully."""
        csv = tmp_path / "customers.csv"
        csv.write_text("customer_id,name,email,city\n101,Rahul,rahul@gmail.com,Bangalore\n")
        df = extract.extract_csv(str(csv), ["customer_id", "name", "email", "city"])
        assert len(df) == 1
        assert "customer_id" in df.columns

    def test_empty_csv(self, tmp_path):
        """CSV with header only and no data rows should raise ValueError."""
        csv = tmp_path / "empty.csv"
        csv.write_text("customer_id,name,email,city\n")
        with pytest.raises(ValueError, match="zero records"):
            extract.extract_csv(str(csv), ["customer_id", "name", "email", "city"])

    def test_missing_column(self, tmp_path):
        """CSV missing a required column should raise ValueError."""
        csv = tmp_path / "missing_col.csv"
        csv.write_text("customer_id,name,email\n101,Rahul,rahul@gmail.com\n")
        with pytest.raises(ValueError, match="Missing required columns"):
            extract.extract_csv(str(csv), ["customer_id", "name", "email", "city"])

    def test_file_not_found(self):
        """Non-existent file path should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            extract.extract_csv("/non/existent/file.csv", ["customer_id"])


# ============================================================
# VALIDATION TESTS
# ============================================================

class TestValidation:

    def _make_customers_df(self):
        return pd.DataFrame({
            "customer_id": [101, 102, 103],
            "name":        ["Rahul", "Arun", "John"],
            "email":       ["rahul@gmail.com", "arun@gmail.com", "john@gmail.com"],
            "city":        ["Bangalore", "Hyderabad", "Chennai"],
        })

    def test_required_columns_pass(self):
        df = self._make_customers_df()
        result = validate.check_required_columns(df, ["customer_id", "name", "email", "city"])
        assert result["status"] == "PASS"

    def test_required_columns_fail(self):
        df = pd.DataFrame({"customer_id": [101], "name": ["Rahul"]})
        result = validate.check_required_columns(df, ["customer_id", "name", "email", "city"])
        assert result["status"] == "FAIL"
        assert "email" in result["message"] or "city" in result["message"]

    def test_empty_file_pass(self):
        df = self._make_customers_df()
        result = validate.check_empty_file(df)
        assert result["status"] == "PASS"

    def test_empty_file_fail(self):
        df = pd.DataFrame(columns=["customer_id", "name", "email", "city"])
        result = validate.check_empty_file(df)
        assert result["status"] == "FAIL"

    def test_null_check_pass(self):
        df = self._make_customers_df()
        result = validate.check_nulls(df, ["customer_id", "name", "email"])
        assert result["status"] == "PASS"

    def test_null_check_fail(self):
        df = self._make_customers_df()
        df.loc[0, "email"] = None  # introduce a null
        result = validate.check_nulls(df, ["customer_id", "name", "email"])
        assert result["status"] == "FAIL"
        assert "email" in result["message"]

    def test_duplicate_check_pass(self):
        df = self._make_customers_df()
        result = validate.check_duplicates(df, "customer_id")
        assert result["status"] == "PASS"

    def test_duplicate_check_fail(self):
        df = pd.DataFrame({
            "customer_id": [101, 101, 102],
            "name":        ["A",  "B",  "C"],
            "email":       ["a@x.com", "b@x.com", "c@x.com"],
            "city":        ["X", "X", "Y"],
        })
        result = validate.check_duplicates(df, "customer_id")
        assert result["status"] == "FAIL"
        assert "101" in result["message"]

    def test_invalid_values_pass(self):
        df = pd.DataFrame({
            "order_id":    [5001, 5002],
            "customer_id": [101, 102],
            "amount":      [100.0, 250.0],
            "status":      ["COMPLETED", "PENDING"],
        })
        result = validate.check_invalid_values(df)
        assert result["status"] == "PASS"

    def test_invalid_values_fail_negative_amount(self):
        df = pd.DataFrame({
            "order_id":    [5001],
            "customer_id": [101],
            "amount":      [-50.0],
            "status":      ["COMPLETED"],
        })
        result = validate.check_invalid_values(df)
        assert result["status"] == "FAIL"
        assert "negative" in result["message"].lower()

    def test_invalid_values_fail_bad_status(self):
        df = pd.DataFrame({
            "order_id":    [5001],
            "customer_id": [101],
            "amount":      [100.0],
            "status":      ["SHIPPED"],   # not an allowed status
        })
        result = validate.check_invalid_values(df)
        assert result["status"] == "FAIL"
        assert "SHIPPED" in result["message"]

    def test_reconciliation_pass(self):
        result = validate.check_reconciliation(100, 100, "Customer Load")
        assert result["status"] == "PASS"

    def test_reconciliation_fail(self):
        result = validate.check_reconciliation(100, 95, "Customer Load")
        assert result["status"] == "FAIL"
        assert "5" in result["message"]


# ============================================================
# INCIDENT TESTS
# ============================================================

class TestIncidents:

    def test_create_incident(self):
        """Creating an incident returns an INC-style ID and inserts into DB."""
        inc_id = incidents.create_incident(
            run_id=1,
            pipeline_name="Customer Load",
            issue="Duplicate customer IDs detected",
            severity="MEDIUM",
        )
        assert inc_id.startswith("INC")
        # Verify it was saved
        inc = incidents.get_incident(inc_id)
        assert inc is not None
        assert inc["status"] == "OPEN"
        assert inc["severity"] == "MEDIUM"

    def test_update_incident_status(self):
        """Updating incident status should be reflected in the DB."""
        inc_id = incidents.create_incident(1, "Order Load", "NULL values found", "LOW")
        incidents.update_incident(inc_id, status="INVESTIGATING")
        inc = incidents.get_incident(inc_id)
        assert inc["status"] == "INVESTIGATING"

    def test_update_incident_resolution(self):
        """Resolving an incident should save the resolution text."""
        inc_id = incidents.create_incident(1, "Order Load", "Data mismatch", "HIGH")
        incidents.update_incident(
            inc_id,
            status="RESOLVED",
            resolution="Reloaded source file and reconciled counts.",
        )
        inc = incidents.get_incident(inc_id)
        assert inc["status"] == "RESOLVED"
        assert "Reloaded source file" in inc["resolution"]

    def test_update_incident_work_notes(self):
        """Work notes should be appended with timestamp."""
        inc_id = incidents.create_incident(1, "Customer Load", "Missing column", "MEDIUM")
        incidents.update_incident(inc_id, work_notes="Checked source file schema.")
        inc = incidents.get_incident(inc_id)
        assert "Checked source file schema." in inc["work_notes"]

    def test_get_all_incidents(self):
        """get_all_incidents should return a list."""
        incidents.create_incident(1, "Pipeline A", "Issue A", "LOW")
        incidents.create_incident(2, "Pipeline B", "Issue B", "HIGH")
        all_incs = incidents.get_all_incidents()
        assert len(all_incs) >= 2

    def test_get_nonexistent_incident(self):
        """Getting a non-existent incident should return None."""
        result = incidents.get_incident("INC9999")
        assert result is None
