# Status: implemented / tested / unverified
Authoring environment: Linux sandbox, Java 21, Python 3.12, PySpark 3.5.3. **No Docker, no real Hadoop/Hive installation was available.**

## Implemented AND executed here (evidence: logs/outputs in `outputs/`)
| Item | Evidence |
|---|---|
| Synthetic data generation (deterministic) | 50,150 raw rows; same result on rerun (md5 stable) |
| Cleaning/validation | `data/cleaning_report.json`: 610 rejected = 150 dup + 120 qty + 100 missing + 80 date + 60 price + 50 category + 50 region; 100 amounts recomputed; 49,540 clean rows |
| Partition tree | 120 partitions, 49,540 rows, no region column in files |
| Docker cluster up | `docker compose ps` shows NameNode, 3 DataNodes, Postgres metastore, HiveServer2 healthy |
| HDFS storage & 3 DataNodes | `Live datanodes (3)` verified in `outputs/hdfs_verification.txt`; fsck replication factor 3.0; checksum match |
| Hive DDL + `MSCK REPAIR TABLE` via Beeline | 120 partitions registered; `outputs/hive_validation.txt` all 5 validation checks pass |
| Hive SQL analytics & totals export | `outputs/hive_analysis.txt` and `outputs/hive_totals.csv` |
| Spark client container built | `retail-dw-spark-client` image with PySpark 3.5.3, OpenJDK 17, Hadoop & Hive confs |
| Spark SQL analytics (Cluster mode reading Hive over HDFS) | `outputs/*.csv`, `outputs/spark_run_info.json` (mode: hive, thrift://hive-metastore:9083, hdfs://namenode:8020) |
| Partition pruning | `outputs/partition_pruning_plan.txt`: 3 of 120 partitions match the filter |
| Charts, insights | `outputs/charts/*.png`, `outputs/business_insights.md` |
| Final validator with Hive cross-check | **33/33 checks pass** (`python -m src.pipeline.validate_outputs --require-hive`) |
| Tests | 29 pytest tests pass in `spark-client` container (`docker compose run --rm spark-client pytest -q`) |

## What remains for project submission (Human tasks)
| Item | Description |
|---|---|
| Screenshots | Capture terminal / UI screenshots per `docs/screenshots_checklist.md` with your username & timestamp |
| Report customization | Fill in institution, team names, and roll numbers in `PROJECT_REPORT.md` and `README.md` |
| Presentation slides | Use `PRESENTATION_OUTLINE.md` to prepare your project presentation |
| GitHub collaboration | Push your feature branches and submit PRs with code reviews |

## Known risks to check first on the cluster
1. **Version mix:** Spark 3.5.3 bundles a Hadoop 3.3.4 client and a Hive 2.3.9 metastore client; the images are Hadoop 2.7.4 and Hive 2.3.2. These usually interoperate, but if Spark fails to connect, try `spark.sql.hive.metastore.version=2.3.9` with `jars=builtin` (already set) or pin an older PySpark (3.1.x/3.2.x).
2. Hive 2.3.2 uses MapReduce for aggregations and can be slow/memory hungry in containers; give Docker >= 6-8 GB.
3. `bde2020/*` images are community images and old; if a tag is unavailable, find the closest `docker-hive` tag and keep the Hadoop/Hive versions consistent.
4. HiveServer2 takes 1-3 minutes to accept connections; the pipeline waits up to 7 minutes.
5. **Observed locally:** Spark ignores `skip.header.line.count` on Hive text tables (staging table showed 49,541 rows incl. the header). Hive honours it. So Spark queries use `sales_partitioned`, never `staging_sales`.
6. Spark runs `local[*]` inside the client container - there is no Spark standalone/YARN cluster.
