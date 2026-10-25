#!/usr/bin/env bash
# Member 2: create database/tables, register partitions, run analysis + validation in Hive.
# Uses beeline inside the hive-server container (sql/ is mounted at /sql).
set -euo pipefail
JDBC="jdbc:hive2://localhost:10000"
BL="docker compose exec -T hive-server beeline -u $JDBC --hivevar DATA_ROOT=/retail --silent=false"
mkdir -p outputs
for f in 01_create_database 02_create_tables 03_create_partitions; do
  echo "=== $f.sql ==="; $BL -f /sql/$f.sql
done
echo "=== 05_validation_queries.sql ==="
$BL -f /sql/05_validation_queries.sql | tee outputs/hive_validation.txt
echo "=== 04_analysis_queries.sql (Hive results) ==="
$BL -f /sql/04_analysis_queries.sql | tee outputs/hive_analysis.txt
echo "=== export totals for the cross-check ==="
docker compose exec -T hive-server beeline -u $JDBC --outputformat=csv2 --silent=true -f /sql/06_export_totals.sql > outputs/hive_totals.csv
cat outputs/hive_totals.csv
grep -q "total_revenue" outputs/hive_totals.csv || { echo "ERROR: Hive totals export failed"; exit 1; }
echo "Hive workflow finished."
