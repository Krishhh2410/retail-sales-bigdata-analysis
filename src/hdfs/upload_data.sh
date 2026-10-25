#!/usr/bin/env bash
# Member 1: upload cleaned data to HDFS. Idempotent (replaces previous copies).
# Run from the repo root in Git Bash / WSL / Linux / macOS.
set -euo pipefail
NN="docker compose exec -T namenode"
[ -f data/retail_sales.csv ] || { echo "ERROR: data/retail_sales.csv missing - run the cleaning step"; exit 1; }
[ -d outputs/warehouse ]    || { echo "ERROR: outputs/warehouse missing - run prepare_partitions"; exit 1; }

echo "[1/5] create HDFS directories"
$NN hdfs dfs -mkdir -p /retail/staging /retail/warehouse
echo "[2/5] copy files into the NameNode container"
CID=$(docker compose ps -q namenode)
docker exec "$CID" rm -rf /tmp/upload && docker exec "$CID" mkdir -p /tmp/upload
docker cp data/retail_sales.csv "$CID":/tmp/upload/retail_sales.csv
docker cp outputs/warehouse "$CID":/tmp/upload/sales
echo "[3/5] staging file -> /retail/staging"
$NN hdfs dfs -put -f /tmp/upload/retail_sales.csv /retail/staging/retail_sales.csv
echo "[4/5] partition tree -> /retail/warehouse/sales (old tree removed first)"
$NN hdfs dfs -rm -r -f /retail/warehouse/sales
$NN hdfs dfs -put /tmp/upload/sales /retail/warehouse/sales
echo "[5/5] listing"
$NN hdfs dfs -ls /retail/staging
$NN hdfs dfs -ls /retail/warehouse/sales
echo "Upload finished."
