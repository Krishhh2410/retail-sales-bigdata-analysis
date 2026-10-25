-- Member 2: Hive analysis queries (HiveQL; also valid Spark SQL).
USE retail_dw;

-- Q1 total revenue
SELECT ROUND(SUM(sales_amount), 2) AS total_revenue FROM sales_partitioned;

-- Q2 total units sold
SELECT SUM(quantity) AS total_units FROM sales_partitioned;

-- Q3 revenue by category
SELECT category, SUM(quantity) AS total_units, ROUND(SUM(sales_amount), 2) AS total_revenue
FROM sales_partitioned GROUP BY category ORDER BY total_revenue DESC;

-- Q4 revenue by region (reads only partition metadata for the grouping column)
SELECT region, SUM(quantity) AS total_units, ROUND(SUM(sales_amount), 2) AS total_revenue
FROM sales_partitioned GROUP BY region ORDER BY total_revenue DESC;

-- Q5 top 10 stores
SELECT store_id, region, ROUND(SUM(sales_amount), 2) AS total_revenue, SUM(quantity) AS total_units
FROM sales_partitioned GROUP BY store_id, region
ORDER BY total_revenue DESC, store_id ASC LIMIT 10;

-- Q6 top 10 products
SELECT product_id, category, SUM(quantity) AS total_units, ROUND(SUM(sales_amount), 2) AS total_revenue
FROM sales_partitioned GROUP BY product_id, category
ORDER BY total_revenue DESC, product_id ASC LIMIT 10;

-- Q7 monthly revenue
SELECT sales_year, sales_month, SUM(quantity) AS total_units, ROUND(SUM(sales_amount), 2) AS total_revenue
FROM sales_partitioned GROUP BY sales_year, sales_month ORDER BY sales_year, sales_month;

-- Q8 yearly revenue
SELECT sales_year, SUM(quantity) AS total_units, ROUND(SUM(sales_amount), 2) AS total_revenue
FROM sales_partitioned GROUP BY sales_year ORDER BY sales_year;

-- Q9 seasonal comparison (season from calendar month; Dec-Feb counted as Winter of the same year)
SELECT sales_year,
       CASE WHEN sales_month IN (12,1,2) THEN 'Winter'
            WHEN sales_month IN (3,4,5)  THEN 'Spring'
            WHEN sales_month IN (6,7,8)  THEN 'Summer'
            ELSE 'Autumn' END AS season,
       SUM(quantity) AS total_units, ROUND(SUM(sales_amount), 2) AS total_revenue
FROM sales_partitioned GROUP BY sales_year,
       CASE WHEN sales_month IN (12,1,2) THEN 'Winter'
            WHEN sales_month IN (3,4,5)  THEN 'Spring'
            WHEN sales_month IN (6,7,8)  THEN 'Summer'
            ELSE 'Autumn' END
ORDER BY sales_year, season;

-- Q10 revenue for one region and a date range -> PARTITION PRUNING
-- Only region=West/sales_year=2025/sales_month 6..8 directories are read.
SELECT ROUND(SUM(sales_amount), 2) AS west_summer_2025_revenue
FROM sales_partitioned
WHERE region = 'West' AND sales_year = 2025 AND sales_month BETWEEN 6 AND 8;

-- Show the pruning in the plan (look for the partition filters / "Partition Description" count):
EXPLAIN EXTENDED
SELECT SUM(sales_amount) FROM sales_partitioned
WHERE region = 'West' AND sales_year = 2025 AND sales_month BETWEEN 6 AND 8;
