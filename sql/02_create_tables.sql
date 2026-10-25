-- Member 2: external tables over HDFS.
-- ${hivevar:DATA_ROOT} is /retail on the cluster (beeline --hivevar DATA_ROOT=/retail).
-- DROP of an EXTERNAL table removes metadata only, never the HDFS files, so this is idempotent.
USE retail_dw;

-- 1) Staging table: the cleaned CSV exactly as uploaded (header + all 9 columns).
DROP TABLE IF EXISTS staging_sales;
CREATE EXTERNAL TABLE staging_sales (
  transaction_id STRING,
  sale_date      STRING,
  region         STRING,
  store_id       STRING,
  product_id     STRING,
  category       STRING,
  quantity       INT,
  unit_price     DECIMAL(12,2),
  sales_amount   DECIMAL(14,2)
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${hivevar:DATA_ROOT}/staging'
TBLPROPERTIES ('skip.header.line.count'='1');

-- 2) Partitioned warehouse table. Partition columns live in the directory names:
--    region=West/sales_year=2025/sales_month=1/part-00000.csv (no header, no region column)
DROP TABLE IF EXISTS sales_partitioned;
CREATE EXTERNAL TABLE sales_partitioned (
  transaction_id STRING,
  sale_date      DATE,
  store_id       STRING,
  product_id     STRING,
  category       STRING,
  quantity       INT,
  unit_price     DECIMAL(12,2),
  sales_amount   DECIMAL(14,2)
)
PARTITIONED BY (region STRING, sales_year INT, sales_month INT)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '${hivevar:DATA_ROOT}/warehouse/sales';
