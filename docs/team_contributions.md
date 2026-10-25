# Contribution matrix (balanced by effort; every member owns code + tests + docs + evidence)
| | Member 1 - Data & HDFS | Member 2 - Hive & orchestration | Member 3 - Spark & reporting |
|---|---|---|---|
| Branch | `feature/data-hdfs` | `feature/hive-warehouse` | `feature/spark-analytics` |
| Code | `src/common.py`, `src/data/generate_data.py`, `clean_data.py`, `prepare_partitions.py`, `src/hdfs/upload_data.sh`, `verify_hdfs.sh` | `sql/01..06*.sql`, `src/hive/run_hive_workflow.sh`, `src/pipeline/run_pipeline.py` | `src/analytics/spark_session.py`, `spark_analysis.py`, `local_analysis.py`, `make_charts.py`, `generate_insights.py`, `src/pipeline/validate_outputs.py` |
| Infrastructure | NameNode + 3 DataNodes, volumes, HDFS settings (`docker-compose.yml` HDFS part, `config/hadoop-hive.env` HDFS keys) | Postgres metastore + HiveServer2 services, partition layout, warehouse design | `docker/spark-client/` (Dockerfile + conf: hive-site, core-site, spark-defaults) |
| Tests | `tests/test_data_quality.py` (cleaning rules, duplicates, generator determinism, partition paths) | Hive validation queries (V1-V5), `tests/test_pipeline_outputs.py`, partition-pruning demonstration | `tests/test_aggregations.py` (pandas oracle + Spark parity), validator checks |
| Docs | `data_dictionary.md`, data/HDFS sections of setup guide + report | warehouse design/partitioning/SQL sections of report, Hive troubleshooting | Spark/results/insights sections of report, charts |
| Evidence to capture | cleaning report, `hdfs dfsadmin -report`, `fsck` output, NameNode UI (3 DataNodes), checksum match | beeline `SHOW PARTITIONS`, query outputs, `EXPLAIN` with pruning, `hive_totals.csv` | Spark run info, CSV reports, charts, `validate_outputs` 31/31 PASS |
| Viva focus | HDFS, replication, blocks, data quality | Hive architecture, metastore, external tables, partitioning | Spark architecture, DataFrames/SQL, Spark vs Hive/MapReduce |

Shared: integration testing, cross-reviews (M1->M3, M2->M1, M3->M2 suggested), end-to-end debugging, report, slides, viva practice, final repo review.
Ground rule: you must be able to explain and re-run your own module live.
