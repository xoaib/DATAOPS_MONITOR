-- =============================================================
-- DataOps Monitor - Database Schema
-- SQLite
-- =============================================================

-- Table: customers
-- Stores customer records loaded from CSV
CREATE TABLE IF NOT EXISTS customers (
    customer_id   INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    email         TEXT    NOT NULL,
    city          TEXT,
    created_at    DATETIME DEFAULT (datetime('now'))
);

-- Table: orders
-- Stores order records loaded from CSV
CREATE TABLE IF NOT EXISTS orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL,
    order_date    TEXT,
    amount        REAL,
    status        TEXT,
    created_at    DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Table: pipeline_runs
-- Tracks every ETL pipeline execution
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name       TEXT    NOT NULL,
    start_time          DATETIME NOT NULL,
    end_time            DATETIME,
    records_processed   INTEGER DEFAULT 0,
    status              TEXT    DEFAULT 'STARTED',  -- STARTED, SUCCESS, FAILED, WARNING
    error_message       TEXT,
    file_path           TEXT
);

-- Table: validation_results
-- Stores the outcome of each data quality check per pipeline run
CREATE TABLE IF NOT EXISTS validation_results (
    validation_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    check_name      TEXT    NOT NULL,
    expected_value  TEXT,
    actual_value    TEXT,
    status          TEXT    NOT NULL,   -- PASS, FAIL
    message         TEXT,
    created_at      DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);

-- Table: incidents
-- ServiceNow-style incident tickets created on pipeline failure
CREATE TABLE IF NOT EXISTS incidents (
    incident_id     TEXT    PRIMARY KEY,  -- e.g. INC0001
    run_id          INTEGER,
    pipeline_name   TEXT    NOT NULL,
    issue           TEXT    NOT NULL,
    severity        TEXT    NOT NULL,    -- LOW, MEDIUM, HIGH, CRITICAL
    status          TEXT    DEFAULT 'OPEN',  -- OPEN, INVESTIGATING, RESOLVED
    created_at      DATETIME DEFAULT (datetime('now')),
    updated_at      DATETIME DEFAULT (datetime('now')),
    resolution      TEXT,
    work_notes      TEXT,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id)
);
