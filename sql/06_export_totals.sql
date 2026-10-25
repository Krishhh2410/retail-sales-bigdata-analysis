-- Single-row result exported by run_hive_workflow.sh (beeline --outputformat=csv2) and
-- compared with the Spark totals by src/pipeline/validate_outputs.py
SELECT COUNT(*) AS row_count, SUM(quantity) AS total_units, ROUND(SUM(sales_amount), 2) AS total_revenue
FROM retail_dw.sales_partitioned;
