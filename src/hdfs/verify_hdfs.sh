#!/usr/bin/env bash
# Member 1: prove the data is really stored in HDFS. Output is also saved to outputs/hdfs_verification.txt
set -euo pipefail
NN="docker compose exec -T namenode"
mkdir -p outputs
{
echo "### DataNode report (expect 'Live datanodes (3)')"
$NN hdfs dfsadmin -report | grep -E "Live datanodes|Name:|DFS Used:|Hostname"
echo; echo "### Safe mode"; $NN hdfs dfsadmin -safemode get
echo; echo "### Directory tree"; $NN hdfs dfs -ls -R /retail | head -40
echo; echo "### Space used"; $NN hdfs dfs -du -h /retail
echo; echo "### fsck: blocks, replication, DataNode locations for the staging file"
$NN hdfs fsck /retail/staging/retail_sales.csv -files -blocks -locations
echo; echo "### First 3 lines of staged file read back from HDFS"
$NN hdfs dfs -cat /retail/staging/retail_sales.csv | head -3
} 2>&1 | tee outputs/hdfs_verification.txt

echo; echo "### Round-trip checksum (local file vs file read back from HDFS)"
LOCAL=$(md5sum data/retail_sales.csv | cut -d' ' -f1 2>/dev/null || md5 -q data/retail_sales.csv)
REMOTE=$($NN hdfs dfs -cat /retail/staging/retail_sales.csv | md5sum | cut -d' ' -f1)
echo "local=$LOCAL hdfs=$REMOTE"
[ "$LOCAL" = "$REMOTE" ] && echo "CHECKSUM MATCH" || { echo "CHECKSUM MISMATCH"; exit 1; }
grep -q "Live datanodes (3)" outputs/hdfs_verification.txt || { echo "ERROR: expected 3 live DataNodes"; exit 1; }
