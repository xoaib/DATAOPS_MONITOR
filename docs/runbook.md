# DataOps Monitor — Operations Runbook

**Project:** DataOps Monitor  
**Role:** Junior Data Engineer  
**Environment:** Local development / Interview demonstration

---

## Purpose

This runbook describes the step-by-step process for running, monitoring, and supporting the DataOps Monitor ETL pipeline system.

---

## Step 1 — Check Input File

Before starting a pipeline, verify the input file is available.

**Manual check (Windows):**
```
dir "data\input\customers.csv"
dir "data\input\orders.csv"
```

**What to look for:**
- File exists in the expected path
- File size is greater than zero
- File is not locked by another process

**If the file is missing:**
- Check with the source team whether the file was generated
- Review the file delivery schedule
- See `troubleshooting.md` → *Missing File* section

---

## Step 2 — Start the Backend

```bash
cd "DataOps Monitor"
uvicorn backend.main:app --reload --port 8000
```

**Expected output:**
```
INFO:     DataOps Monitor API starting...
INFO:     Database initialised successfully.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Verify the API is running:**
- Open browser: `http://127.0.0.1:8000/api/health`
- Expected: `{"status": "ok", "service": "DataOps Monitor"}`

---

## Step 3 — Open the Dashboard

Open `frontend/index.html` in your browser.

The API Status indicator (top right) should show:
```
● API Online
```

If it shows `API Offline`:
- Confirm the backend is running (Step 2)
- Check the console for CORS or connection errors

---

## Step 4 — Run a Pipeline

1. In the **Run Pipeline** section, select the pipeline from the dropdown:
   - `Customer Load (customers.csv)` — normal run
   - `Order Load (orders.csv)` — normal run
   - Test cases for failure demonstration

2. Click **▶ Run Pipeline**

3. Wait for the result (displayed below the button):
   - **SUCCESS** — green result box
   - **FAILED** — red result box (incident created automatically)
   - **WARNING** — amber result box (reconciliation mismatch)

---

## Step 5 — Monitor Pipeline Status

The **Pipeline Runs** table shows all executions.

**Status meanings:**

| Status  | Meaning |
|---------|---------|
| STARTED | Pipeline is currently executing |
| SUCCESS | All steps completed, all records loaded |
| FAILED  | A validation or load error occurred |
| WARNING | Data loaded but reconciliation mismatch detected |

**What to check on FAILED:**
- See the Error column for the failure message
- Check `logs/pipeline.log` for detailed trace
- Open the auto-created incident ticket

---

## Step 6 — Review Validation Results

Open the **Validation Results** section.

Each pipeline run shows these checks:

| Check | What it verifies |
|-------|-----------------|
| Required Column Check | All expected columns present |
| Empty File Check | File has at least 1 data row |
| NULL Check | No missing values in required fields |
| Duplicate Check | No duplicate customer/order IDs |
| Invalid Value Check | Amounts ≥ 0, status in allowed set |
| Source-to-Target Reconciliation | Source count = target count |

**PASS** = check succeeded  
**FAIL** = check failed, see message column for details

---

## Step 7 — Review and Resolve Incidents

If a pipeline fails, an incident is automatically created.

**Open the Incidents section** to see open tickets.

**To investigate:**
1. Click **View / Update** on the incident
2. Read the issue description
3. Change status from `OPEN` → `INVESTIGATING`
4. Add work notes describing your investigation steps
5. When resolved, add a resolution and set status to `RESOLVED`

**Workflow:**
```
OPEN → INVESTIGATING → RESOLVED
```

---

## Step 8 — Generate Operational Report

Click **Generate Report** to produce today's daily summary.

The report shows:
- Total pipeline runs
- Success / failure counts
- Records processed
- Open incidents
- Validation issues

This report can be used for daily stand-ups, manager updates, or handover notes.

---

## Step 9 — Check Log File

Logs are written to:
```
logs/pipeline.log
```

**Log levels:**

| Level   | When used |
|---------|-----------|
| INFO    | Normal pipeline activity |
| WARNING | Validation issue detected, pipeline may continue |
| ERROR   | Critical failure, pipeline stopped |

**Useful log entries to look for:**
```
PIPELINE STARTED: Customer Load
Extraction successful. Records: 5
All validation checks passed.
Transformation complete.
Loaded 5 customer records.
PIPELINE COMPLETED SUCCESSFULLY
```

---

## Escalation

If you cannot resolve an issue with first-level troubleshooting:

1. Document all steps taken in the incident work notes
2. Capture the error from `logs/pipeline.log`
3. Note the `run_id` of the failed pipeline run
4. Escalate to the Senior Data Engineer with the incident ID and log extract
