-- Member 2: register the partition directories that already exist in HDFS.
-- MSCK REPAIR scans the table LOCATION and adds every region=/sales_year=/sales_month= directory.
-- It is idempotent: already-registered partitions are left alone.
USE retail_dw;
MSCK REPAIR TABLE sales_partitioned;
SHOW PARTITIONS sales_partitioned;

-- Manual alternative for a single partition (useful for explaining in the viva):
-- ALTER TABLE sales_partitioned ADD IF NOT EXISTS
--   PARTITION (region='West', sales_year=2025, sales_month=1)
--   LOCATION '${hivevar:DATA_ROOT}/warehouse/sales/region=West/sales_year=2025/sales_month=1';
