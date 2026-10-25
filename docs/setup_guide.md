# Setup guide

## 1. Software
| Need | Why | Check |
|---|---|---|
| Python 3.10+ | scripts, pandas, matplotlib | `python --version` |
| Java 8/11/17/21 | PySpark 3.5.3 (local mode) | `java -version` |
| Docker Desktop (WSL2 backend on Windows), >= 8 GB RAM for the VM | HDFS/Hive cluster | `docker compose version` |
| Git (Git for Windows includes Git Bash) | version control, runs the `.sh` scripts | `git --version` |

Compatibility: PySpark 3.5.x supports Java 8/11/17/21 (not Java 24+ without checking release notes). Do not mix an arbitrary Hadoop/Hive/Spark install - the Docker stack pins consistent images; the Spark client image pins Java 17 + PySpark 3.5.3.

## 2. Python environment
Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
java -version
```
Linux/macOS:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && java -version
```
**Windows + local PySpark:** native Windows needs `winutils.exe`/`HADOOP_HOME`. Avoid it - run local mode inside WSL2, or inside the container:
```powershell
docker compose build spark-client
docker compose run --rm spark-client python -m src.pipeline.run_pipeline --mode local
```

## 3. Local mode (no Docker)
```bash
python -m src.pipeline.run_pipeline --mode local
python -m pytest -q
```

## 4. Cluster mode - step by step
Run the `.sh` scripts from **Git Bash or WSL** in the repo root (they call `docker compose`).
```bash
python -m src.data.generate_data && python -m src.data.clean_data && python -m src.data.prepare_partitions
docker compose up -d --build          # 1. start
docker compose ps                     #    namenode, datanode1-3, hive-* should be Up
docker compose exec -T namenode hdfs dfsadmin -report | grep "Live datanodes"   # 2-3. expect (3)
# NameNode UI: http://localhost:50070  (Datanodes tab)
bash src/hdfs/upload_data.sh          # 4-6. mkdir, put, ls
bash src/hdfs/verify_hdfs.sh          # 7-9. cat, fsck blocks/replication, checksum round trip
bash src/hive/run_hive_workflow.sh    # DDL, MSCK REPAIR, validation, analysis, hive_totals.csv
docker compose run --rm spark-client python -m src.analytics.spark_analysis --mode hive
python -m src.analytics.make_charts && python -m src.analytics.generate_insights
python -m src.pipeline.validate_outputs --require-hive
```
Or everything: `python -m src.pipeline.run_pipeline --mode cluster`.

PowerShell equivalents for the HDFS commands:
```powershell
docker compose exec -T namenode hdfs dfs -ls -R /retail
docker compose exec -T namenode hdfs fsck /retail/staging/retail_sales.csv -files -blocks -locations
docker compose exec hive-server beeline -u jdbc:hive2://localhost:10000 -e "SHOW DATABASES;"
```

### Stop / restart without losing data
```bash
docker compose stop            # keeps containers and named volumes
docker compose start           # data still in HDFS
docker compose down            # removes containers, KEEPS volumes (namenode_data, datanode*_data, metastore_pg)
docker compose down -v         # DESTROYS volumes = deletes HDFS data and metastore (only for a clean reset)
```
After a restart, re-run `docker compose exec -T namenode hdfs dfsadmin -report` and wait for 3 live DataNodes; the NameNode stays in safe mode briefly.

## 5. Logs and troubleshooting
| Symptom | Fix |
|---|---|
| `docker compose logs namenode` shows format/ClusterID errors | volumes from an older run: `docker compose down -v` and start again |
| Only 1-2 live DataNodes | `docker compose logs datanode2`; wait 30 s; `docker compose restart datanode2` |
| beeline: `Connection refused` | HiveServer2 still starting (1-3 min) - `docker compose logs hive-server` |
| Hive `MSCK` finds 0 partitions | wrong location: run `DESCRIBE FORMATTED retail_dw.sales_partitioned;` and `hdfs dfs -ls -R /retail/warehouse/sales`; directory names must be exactly `region=West/sales_year=2025/sales_month=1` |
| All Hive values NULL | delimiter/column mismatch - partition files must have 8 columns, no header, no region |
| Out-of-memory / killed containers | Docker Desktop -> Settings -> Resources -> raise memory to 8 GB |
| Spark cannot reach metastore | run inside `spark-client` (not on the host); check `docker/spark-client/conf/hive-site.xml` |
| Spark/Hive version errors | see "Known risks" in `docs/STATUS.md` |
| `Bad substitution` / `\r` errors in `.sh` on Windows | save scripts with LF endings (`git config core.autocrlf input`) |
| Port 50070 or 10000 in use | change the left side of the port mapping in `docker-compose.yml` |
If the whole stack is too heavy for your laptop, demonstrate **local mode** plus screenshots from a lab machine/Linux VM, and say so honestly.
