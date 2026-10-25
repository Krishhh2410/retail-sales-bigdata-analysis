-- Member 2: sanity checks on the warehouse. Compare with outputs from the Python validator.
USE retail_dw;

-- V1 staging vs partitioned totals must match (same rows, two layouts)
SELECT 'staging' AS src, COUNT(*) AS row_count, SUM(quantity) AS total_units, ROUND(SUM(sales_amount),2) AS total_revenue FROM staging_sales
UNION ALL
SELECT 'partitioned', COUNT(*), SUM(quantity), ROUND(SUM(sales_amount),2) FROM sales_partitioned;

-- V2 no duplicate transaction ids (expect 0 rows)
SELECT transaction_id, COUNT(*) AS c FROM sales_partitioned GROUP BY transaction_id HAVING COUNT(*) > 1 LIMIT 5;

-- V3 no NULLs introduced by a schema/delimiter mismatch (expect all zeros)
SELECT SUM(CASE WHEN sale_date IS NULL THEN 1 ELSE 0 END) AS null_dates,
       SUM(CASE WHEN quantity IS NULL THEN 1 ELSE 0 END) AS null_qty,
       SUM(CASE WHEN unit_price IS NULL THEN 1 ELSE 0 END) AS null_price,
       SUM(CASE WHEN sales_amount IS NULL THEN 1 ELSE 0 END) AS null_amount
FROM sales_partitioned;

-- V4 sales_amount = quantity * unit_price (expect 0)
SELECT COUNT(*) AS bad_amounts FROM sales_partitioned
WHERE ABS(sales_amount - quantity * unit_price) > 0.01;

-- V5 rows per partition (spot check)
SELECT region, sales_year, sales_month, COUNT(*) AS rows_in_partition
FROM sales_partitioned GROUP BY region, sales_year, sales_month
ORDER BY region, sales_year, sales_month LIMIT 12;
