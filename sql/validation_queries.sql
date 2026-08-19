-- =============================================================
-- DataOps Monitor - Validation Queries
-- Simple SQL queries used by junior data engineers
-- to validate data quality and monitor pipeline health.
-- =============================================================


-- ------------------------------------------------------------
-- Query 1: Total record count
-- How many customer records exist in the database?
-- ------------------------------------------------------------
SELECT COUNT(*) AS total_customers
FROM customers;


-- ------------------------------------------------------------
-- Query 2: Duplicate records
-- Find any duplicate customer IDs that should not exist.
-- ------------------------------------------------------------
SELECT customer_id, COUNT(*) AS occurrences
FROM customers
GROUP BY customer_id
HAVING COUNT(*) > 1;


-- ------------------------------------------------------------
-- Query 3: NULL values check
-- Find customers with missing email addresses (required field).
-- ------------------------------------------------------------
SELECT customer_id, name
FROM customers
WHERE email IS NULL OR TRIM(email) = '';


-- ------------------------------------------------------------
-- Query 4: Orders grouped by status
-- How many orders are in each status bucket?
-- ------------------------------------------------------------
SELECT status, COUNT(*) AS total_orders
FROM orders
GROUP BY status
ORDER BY total_orders DESC;


-- ------------------------------------------------------------
-- Query 5: Records grouped by city
-- Which cities have the most customers?
-- ------------------------------------------------------------
SELECT city, COUNT(*) AS customer_count
FROM customers
GROUP BY city
ORDER BY customer_count DESC;


-- ------------------------------------------------------------
-- Query 6: Failed pipeline runs
-- Show all pipeline runs that ended with a FAILED status.
-- ------------------------------------------------------------
SELECT run_id, pipeline_name, start_time, end_time, error_message
FROM pipeline_runs
WHERE status = 'FAILED'
ORDER BY start_time DESC;


-- ------------------------------------------------------------
-- Query 7: Open incidents
-- Show all incidents that have not been resolved yet.
-- ------------------------------------------------------------
SELECT incident_id, pipeline_name, issue, severity, status, created_at
FROM incidents
WHERE status IN ('OPEN', 'INVESTIGATING')
ORDER BY created_at DESC;


-- ------------------------------------------------------------
-- Query 8: Source vs target count
-- Compare how many records were processed vs loaded.
-- Source = records_processed from pipeline_runs.
-- Target = actual rows in the target table (customers shown here).
-- ------------------------------------------------------------
SELECT
    pr.run_id,
    pr.pipeline_name,
    pr.records_processed                        AS source_count,
    (SELECT COUNT(*) FROM customers)            AS target_count,
    pr.records_processed - (SELECT COUNT(*) FROM customers) AS difference
FROM pipeline_runs pr
WHERE pr.pipeline_name LIKE '%Customer%'
ORDER BY pr.run_id DESC
LIMIT 1;


-- ------------------------------------------------------------
-- Query 9: Missing records check
-- Find orders where the customer_id does not exist in customers.
-- These are orphaned records - a data integrity problem.
-- ------------------------------------------------------------
SELECT o.order_id, o.customer_id, o.amount, o.status
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;


-- ------------------------------------------------------------
-- Query 10: Daily pipeline summary
-- How many pipelines ran today, and what was the outcome?
-- ------------------------------------------------------------
SELECT
    DATE(start_time)                                    AS run_date,
    COUNT(*)                                            AS total_runs,
    SUM(CASE WHEN status = 'SUCCESS'  THEN 1 ELSE 0 END) AS successful,
    SUM(CASE WHEN status = 'FAILED'   THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN status = 'WARNING'  THEN 1 ELSE 0 END) AS warnings,
    SUM(records_processed)                              AS total_records
FROM pipeline_runs
WHERE DATE(start_time) = DATE('now')
GROUP BY DATE(start_time);
