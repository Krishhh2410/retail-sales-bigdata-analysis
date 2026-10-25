# Presentation outline (12 slides, ~15 min) - speaker in brackets
1. Title, team, guide [M1] 2. Problem statement & motivation [M1] 3. Objectives [M2] 4. Technology stack [M2]
5. Architecture diagram (Mermaid) and honest cluster note [M3] 6. Dataset (synthetic) & preprocessing - show `cleaning_report.json` [M1]
7. HDFS: 1 NameNode + 3 DataNodes, replication, fsck [M1] 8. Hive: schema, external tables, partitioning, pruning [M2]
9. Spark: Hive integration, aggregations [M3] 10. Results & charts (actual numbers) [M3] 11. Testing, GitHub contributions, limitations [M2]
12. Conclusion & future scope (Parquet/ORC, real cluster, YARN, streaming) [All]

# Live demo script (~8 min). Run beforehand once so images/volumes are cached.
| Step | Command | Expect | Who explains |
|---|---|---|---|
| 1 | `python -m src.data.clean_data` then `cat data/cleaning_report.json` | 50,150 in -> 49,540 clean, 610 rejected by reason | M1 |
| 2 | `docker compose ps`; open http://localhost:50070 | 3 live DataNodes | M1 |
| 3 | `bash src/hdfs/upload_data.sh && bash src/hdfs/verify_hdfs.sh` | files listed, replication 3, CHECKSUM MATCH | M1 |
| 4 | `bash src/hive/run_hive_workflow.sh` (or beeline `SHOW PARTITIONS`) | 120 partitions, query results | M2 |
| 5 | `EXPLAIN` / `outputs/partition_pruning_plan.txt` | pruned partitions | M2 |
| 6 | `docker compose run --rm spark-client python -m src.analytics.spark_analysis --mode hive` | CSV reports written, `spark_run_info.json` | M3 |
| 7 | open `outputs/charts/*.png`, `business_insights.md` | charts + computed insights | M3 |
| 8 | `python -m src.pipeline.validate_outputs --require-hive` | all checks PASS | M2 |
| 9 | GitHub contributors / PR page | three people's real commits | All |
Fallback if the cluster won't start: `python -m src.pipeline.run_pipeline --mode local` and say clearly that it is local mode.
