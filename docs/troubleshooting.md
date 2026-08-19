# DataOps Monitor — Troubleshooting Guide

**Project:** DataOps Monitor  
**Role:** Junior Data Engineer  
**Audience:** First-level support

---

## Overview

This guide covers the most common pipeline failure scenarios and their recommended actions.

> **Important:** This system provides first-level diagnosis and escalation information.  
> Complex production issues should be escalated to a Senior Data Engineer.

---

## Issue 1: Missing Input File

**Symptom:**
```
Pipeline status: FAILED
Error: Input file not found: data/input/customers.csv
```

**Validation check:** File Exists check fails immediately.

**Cause:**
- Source file was not delivered on time
- Incorrect file path configured
- File delivered to wrong directory
- Upstream process failed

**Recommended Actions:**
1. Navigate to `data/input/` and confirm the file is missing
2. Check the file delivery schedule with the source team
3. Verify the expected file name and path are correct
4. Ask the source team to resend the file
5. If automated: check whether the upstream job succeeded

**Log message:**
```
ERROR | extract | Input file not found: data/input/customers.csv
```

---

## Issue 2: Empty File

**Symptom:**
```
Pipeline status: FAILED
Error: Input file contains zero records.
```

**Validation check:** Empty File Check fails.

**Cause:**
- Source system generated an empty file (possible upstream failure)
- File was truncated during transfer
- File contains only a header row and no data rows

**Recommended Actions:**
1. Open the file and check whether it contains only a header row
2. Contact the source team to confirm whether data was generated
3. Check if the upstream source system had any errors today
4. If the issue is intermittent, check whether a retry is safe

**Log message:**
```
WARNING | validate | Empty File Check — FAIL: Input file contains zero records.
```

---

## Issue 3: Missing Column

**Symptom:**
```
Pipeline status: FAILED
Error: Missing required columns: ['city']. Expected: ['customer_id', 'name', 'email', 'city']
```

**Validation check:** Required Column Check fails.

**Cause:**
- Source team changed the file schema (column removed or renamed)
- Column name has extra whitespace or different capitalisation
- Wrong file version delivered

**Recommended Actions:**
1. Open the CSV file and compare its columns with the expected schema
2. Check if a column was renamed (e.g. `City` vs `city`)
3. Confirm with the source team whether the schema changed intentionally
4. If the schema changed permanently, update `CUSTOMER_COLUMNS` in `pipeline.py`

**Expected schema:**
```
customers: customer_id, name, email, city
orders:    order_id, customer_id, order_date, amount, status
```

**Log message:**
```
ERROR | extract | Missing required columns: ['city']
```

---

## Issue 4: Duplicate Records

**Symptom:**
```
Pipeline status: FAILED
Error: Duplicate customer_id(s) found: [102]
```

**Validation check:** Duplicate Check fails.

**Cause:**
- Source system sent duplicate records
- File was accidentally concatenated twice
- Previous file was resent without deduplication

**Recommended Actions:**
1. Open the CSV file and filter for the duplicate ID(s) listed in the error
2. Determine which record is the correct/latest version
3. Remove the duplicate record from the file manually
4. Rerun the pipeline using the corrected file
5. Notify the source team about the duplicate records for their investigation

**SQL to check duplicates in the database:**
```sql
SELECT customer_id, COUNT(*) AS cnt
FROM customers
GROUP BY customer_id
HAVING COUNT(*) > 1;
```

**Log message:**
```
WARNING | validate | Duplicate Check — FAIL: Duplicate customer_id(s) found: [102]
```

---

## Issue 5: NULL Values

**Symptom:**
```
Pipeline status: FAILED
Error: 'email' has 2 null/empty value(s)
```

**Validation check:** NULL Check fails.

**Cause:**
- Required fields are missing in the source file
- Source system sent incomplete records

**Recommended Actions:**
1. Open the CSV and identify the rows with null values
2. Determine if the nulls are expected (optional field) or a data quality issue
3. If unexpected: contact the source team to send corrected records
4. If acceptable: update the validation rules to allow nulls in that field

**SQL to find nulls in the database:**
```sql
SELECT customer_id, name, email, city
FROM customers
WHERE email IS NULL OR TRIM(email) = '';
```

**Log message:**
```
WARNING | validate | NULL Check — FAIL: 'email' has 2 null/empty value(s)
```

---

## Issue 6: Invalid Values

**Symptom:**
```
Pipeline status: FAILED
Error: 1 row(s) have negative amount; Invalid status value(s): ['SHIPPED']
```

**Validation check:** Invalid Value Check fails.

**Cause:**
- Source system sent a negative amount (data entry error or refund record)
- Order status value not in the allowed set
- Data type mismatch (e.g. text in a numeric field)

**Allowed order statuses:**
```
PENDING, COMPLETED, CANCELLED
```

**Recommended Actions:**
1. Open the CSV and locate the invalid row(s)
2. For negative amounts: confirm whether this is a refund or a data error
3. For invalid statuses: check whether the source system uses a different value set
4. Correct the values or update the validation rules if the new status is valid
5. Rerun the pipeline

**SQL to check order statuses:**
```sql
SELECT status, COUNT(*) AS cnt
FROM orders
GROUP BY status;
```

---

## Issue 7: Database Load Failure

**Symptom:**
```
Pipeline status: FAILED
Error: Unexpected error during pipeline execution: database is locked
```

**Cause:**
- Database file is locked by another process
- Disk space full
- Permissions issue on the database file
- Corrupted database file

**Recommended Actions:**
1. Check if another pipeline run is currently executing
2. Check available disk space
3. Check file permissions on `dataops.db`
4. Restart the backend server if safe to do so
5. If the database appears corrupted, restore from the last backup

**Log message:**
```
ERROR | pipeline | Unexpected error during pipeline execution: ...
```

---

## Issue 8: Source-to-Target Data Mismatch

**Symptom:**
```
Pipeline status: WARNING
Error: Mismatch: 5 record(s) lost in target
Validation: Source-to-Target Reconciliation — FAIL
```

**Cause:**
- Some records failed to load (invalid data type, constraint violation)
- Transaction partially rolled back
- Transformation step dropped rows

**Recommended Actions:**
1. Note the difference count from the reconciliation result
2. Check `logs/pipeline.log` for any "Skipping row" warnings during the load step
3. Run the reconciliation SQL query to identify missing records:
```sql
SELECT o.order_id, o.customer_id
FROM orders_source o
LEFT JOIN orders t ON o.order_id = t.order_id
WHERE t.order_id IS NULL;
```
4. Identify the specific records that were not loaded
5. Fix the root cause and reload the pipeline

---

## Escalation Criteria

Escalate to a Senior Data Engineer when:
- The same pipeline fails more than 3 times consecutively
- Data mismatch exceeds 5% of total records
- The database file appears corrupted
- A source schema change requires code changes to the pipeline
- An incident is not resolvable within your defined SLA
