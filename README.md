# DataOps Monitor

Data Engineer Project

> A functional Data Pipeline Monitoring & Validation System that demonstrates core junior data engineering skills: ETL, SQL, data validation, pipeline monitoring, incident management, production support, and operational reporting.

---

## Project Overview

DataOps Monitor simulates how a junior data engineer monitors and supports scheduled data pipelines in a production-support environment.

The system accepts CSV data, runs it through a complete ETL pipeline, validates data quality, loads records into a database, performs source-to-target reconciliation, monitors pipeline health, and manages incidents when failures occur — all accessible through a clean web dashboard.

> **ServiceNow Disclaimer:**  
> ServiceNow functionality is simulated locally to demonstrate incident-management and ticket-update concepts. No real ServiceNow integration is used.

---

## Business Scenario

A company receives daily customer and order data as CSV files from an upstream source system. A junior data engineer is responsible for:

- Running the daily data pipeline
- Validating incoming data quality
- Loading validated records into the database
- Monitoring pipeline success or failure
- Investigating and resolving incidents when the pipeline fails
- Generating a daily operational report for the team

DataOps Monitor simulates exactly this workflow.

---

## Architecture

```
CSV File
   ↓
File Validation       ← Does the file exist? Is it readable? Not empty?
   ↓
Data Extraction       ← Read CSV using Pandas
   ↓
Data Validation       ← Column check, NULL check, duplicate check, value check
   ↓
Transformation        ← Clean whitespace, standardise city/status, parse dates
   ↓
Database Load         ← Insert into SQLite (with transaction)
   ↓
SQL Validation        ← Source-to-target reconciliation
   ↓
Pipeline Monitoring   ← Record run status in pipeline_runs table
   ↓
SUCCESS / FAILED
   ↓
If Failed:
   Log Error → Create Incident → Investigate → Resolve
   ↓
Operational Report
   ↓
Web Dashboard
```

---

## Core Skills Demonstrated

| Skill | Where demonstrated |
|---|---|
| **SQL** | `sql/schema.sql`, `sql/validation_queries.sql`, all DB queries |
| **ETL / ELT** | `backend/extract.py`, `backend/transform.py`, `backend/pipeline.py` |
| **Data Validation** | `backend/validate.py` — 6 validation checks |
| **Pipeline Monitoring** | `backend/monitor.py`, `pipeline_runs` table |
| **Incident Management** | `backend/incidents.py`, `incidents` table |
| **Production Support** | Full pipeline retry and failure workflow |
| **ServiceNow-style Tickets** | Incident modal: OPEN → INVESTIGATING → RESOLVED |
| **First-Level Troubleshooting** | `docs/troubleshooting.md`, structured error messages |
| **Operational Reporting** | `backend/reports.py`, daily report endpoint |
| **Documentation** | `docs/runbook.md`, `docs/troubleshooting.md`, this README |

---

## Technologies

| Layer | Technology |
|---|---|
| Backend | Python 3.x, FastAPI, Pandas |
| Database | SQLite (file-based, zero setup) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Logging | Python `logging` module |
| Testing | pytest |

---

## Project Structure

```
DataOps Monitor/
├── backend/
│   ├── main.py          # FastAPI app — all API endpoints
│   ├── database.py      # SQLite init and connection helper
│   ├── models.py        # Pydantic request/response models
│   ├── pipeline.py      # Full ETL orchestration
│   ├── extract.py       # CSV extraction and file validation
│   ├── transform.py     # Data cleaning and standardisation
│   ├── validate.py      # Data quality checks
│   ├── monitor.py       # Pipeline run tracking
│   ├── incidents.py     # Incident ticket management
│   └── reports.py       # Operational report generator
│
├── frontend/
│   ├── index.html       # Single-page dashboard
│   ├── style.css        # Dark-mode professional design
│   └── script.js        # fetch()-based JavaScript
│
├── data/
│   ├── input/
│   │   ├── customers.csv      # Valid customer data
│   │   └── orders.csv         # Valid order data
│   └── test_cases/
│       ├── duplicate_records.csv
│       ├── missing_column.csv
│       ├── null_values.csv
│       ├── invalid_values.csv
│       └── empty_file.csv
│
├── sql/
│   ├── schema.sql             # Database schema (5 tables)
│   └── validation_queries.sql # 10 SQL validation queries
│
├── logs/
│   └── pipeline.log           # Auto-created on first run
│
├── docs/
│   ├── runbook.md
│   └── troubleshooting.md
│
├── tests/
│   └── test_pipeline.py
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/xoaib/DATAOPS_MONITOR.git
cd DATAOPS_MONITOR
```

### 2. Create a Python virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Copy environment variables

```bash
cp .env.example .env
```

No changes required — SQLite is used by default.

---

## How to Run

### Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Expected output:
```
INFO:     DataOps Monitor API starting...
INFO:     Database initialised successfully.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Open the dashboard

Open `frontend/index.html` directly in your browser.

The **API Online** indicator should appear green in the top-right corner.

### Verify the API

```
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/docs       ← FastAPI auto-generated documentation
```

