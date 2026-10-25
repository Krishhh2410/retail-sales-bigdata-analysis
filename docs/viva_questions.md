# Viva questions and answers (50)
Answers are short on purpose - explain them in your own words. Our facts: synthetic data, 49,540 clean rows, 1 NameNode + 3 DataNodes in Docker, Hive external tables partitioned by region/year/month, Spark reading the Hive table.

## A. Big Data and Hadoop
1. **What is Big Data?** Data too large, fast or varied for one machine/traditional tools; usually described by volume, velocity, variety. Our dataset is small - it demonstrates the *architecture*, not true big-data scale.
2. **Is 50k rows big data?** No. We use the same tools and patterns that scale; we say that openly.
3. **What is Hadoop?** A framework for distributed storage (HDFS) and processing (MapReduce/YARN) on commodity machines.
4. **Why distributed storage?** One disk/machine limits capacity and is a single point of failure; HDFS splits files across machines and replicates them.
5. **Which Hadoop parts do we actually use?** HDFS only. We do not run YARN or MapReduce ourselves (Hive's engine in the image may use MapReduce internally).

## B. HDFS
6. **NameNode vs DataNode?** NameNode stores metadata (file tree, block locations); DataNodes store the actual blocks and report to the NameNode with heartbeats.
7. **What is a block?** Files are cut into fixed-size blocks (128 MB default in Hadoop 3, 64 MB in 2.x). Our 3 MB file fits in one block - it is replicated, not split.
8. **What is replication?** Each block is copied to several DataNodes (we set 3) so one failure loses nothing.
9. **What happens when a DataNode dies?** The NameNode stops getting heartbeats, marks it dead and re-replicates its blocks from the remaining copies.
10. **Is the NameNode a single point of failure?** In our setup yes (no HA/standby). Production uses HA NameNodes.
11. **Is your cluster a real 3-node cluster?** No - one NameNode and three DataNode *containers* on one machine. It shows replication logic, not real hardware fault tolerance or performance.
12. **How did you verify storage?** `hdfs dfsadmin -report` (3 live), `hdfs dfs -ls`, `hdfs fsck -blocks -locations`, and an md5 round-trip of the file.
13. **Why can't you edit a file in HDFS?** HDFS is write-once/append-oriented; designed for large sequential reads, not random updates.
14. **Why `docker compose down` vs `down -v`?** `down` keeps named volumes (data survives); `-v` deletes them (HDFS data and metastore lost).

## C. Hive
15. **What is Hive?** SQL-like data warehouse layer over files in HDFS; HiveQL queries are compiled into jobs (MapReduce/Tez/Spark).
16. **Is Hive a database?** No - it does not store data itself; data stays in HDFS, metadata in the metastore.
17. **What is the metastore?** A relational DB (PostgreSQL here) holding table schemas, locations and partitions.
18. **External vs managed table?** Dropping a managed table deletes its data; dropping an external table deletes only metadata. We use external so a `DROP TABLE` can never destroy the HDFS files and our DDL is re-runnable.
19. **Why a staging table and a partitioned table?** Staging mirrors the cleaned CSV (with header, 9 columns) for validation; the partitioned table is the optimised warehouse layout.
20. **What is partitioning?** Splitting a table into directories by column values (`region=West/sales_year=2025/sales_month=1`) so queries can skip irrelevant data.
21. **What is partition pruning?** The engine reads only partitions that satisfy filters on partition columns. Our Spark plan showed 3 of 120 partitions for `West / 2025 / months 6-8`.
22. **Why not partition by store or product?** Too many small partitions (small-files problem, metastore overhead). Region/year/month gives 120 reasonably sized partitions.
23. **Why are partition columns not in the files?** Hive takes their values from the directory names; duplicating them would break the schema/column order.
24. **What does `MSCK REPAIR TABLE` do?** Scans the table location and registers partition directories missing from the metastore. Alternative: `ALTER TABLE ... ADD PARTITION`.
25. **What if you upload data but forget MSCK?** The queries return nothing/less because the metastore doesn't know the partitions.
26. **How do you handle the CSV header?** Staging uses `skip.header.line.count=1`; partition files are written without header.
27. **Why DECIMAL for money?** Avoids floating-point rounding errors; we still compare totals with a 0.01 tolerance because Python/Spark sums use doubles in places.
28. **Why is Hive slower than Spark here?** Hive 2.3 uses MapReduce (disk-based) in the image; Spark keeps intermediate data in memory.
29. **Can Hive and Spark share tables?** Yes - both use the same metastore and read the same HDFS files.

## D. Spark
30. **What is Spark?** A distributed in-memory data processing engine with SQL, DataFrame, streaming and ML APIs.
31. **Spark vs MapReduce?** Spark keeps intermediate results in memory and uses a DAG of operations, so iterative/multi-stage jobs are much faster; MapReduce writes to disk between stages.
32. **Spark vs Hive?** Spark is an engine; Hive is a warehouse/metadata layer with its own SQL compiler. Spark can use Hive's metastore.
33. **What is Spark SQL / a DataFrame?** DataFrames are distributed tables with named columns; Spark SQL lets you query them with SQL; both go through the same optimizer (Catalyst).
34. **How does Spark know where the Hive table is?** `enableHiveSupport()` plus `hive-site.xml` (`hive.metastore.uris`) -> asks the metastore for schema/location/partitions, then reads HDFS (`core-site.xml` gives `fs.defaultFS`).
35. **Does Spark copy the Hive data?** No, it reads the files in place.
36. **Is your Spark running on a cluster?** No. It runs in `local[*]` inside one container - multi-core on one machine. A real cluster would add a standalone/YARN/Kubernetes master and workers.
37. **What is lazy evaluation?** Transformations build a plan; nothing runs until an action (like `toPandas`/`collect`/write) is called.
38. **Why `toPandas()` in your code - isn't that cheating?** Spark did all aggregation; only the *small result tables* (<= 24 rows) are collected to the driver to write CSV. Never collect raw data.
39. **What is a shuffle?** Redistribution of data between partitions (needed for `GROUP BY`/`ORDER BY`). `spark.sql.shuffle.partitions=8` keeps it small for our data.
40. **Why does Spark staging count one extra row?** Spark ignores Hive's `skip.header.line.count` on text tables (observed). Hive honours it. We query the partitioned table in Spark.
41. **What is a pandas fallback for?** `local_analysis.py` is only a test oracle; Spark results are compared against it. It is never presented as Spark.

## E. Data quality and logic
42. **Which problems do you detect?** Missing values, duplicates, invalid dates/quantities/prices, unexpected categories/regions, wrong amounts. Counts are in `cleaning_report.json`.
43. **Why recompute `sales_amount`?** It is a derived column; a wrong stored value must not corrupt revenue.
44. **How do you know Hive = Spark = source?** `validate_outputs.py` compares row counts, units, revenue (0.01 tolerance) across cleaned CSV, partition files, Spark and Hive export.
45. **How is "seasonal" defined?** By calendar month (Winter 12-2, Spring 3-5, Summer 6-8, Autumn 9-11). December counts as winter of the same year - a simplification.
46. **Is the insight real?** No - the data is synthetic with built-in seasonality, so the insights show the method only.

## F. Engineering and teamwork
47. **How is the pipeline idempotent?** External-table DROP/CREATE, `MSCK` is idempotent, HDFS put replaces the old tree, partitions rebuilt from scratch, outputs overwritten.
48. **What if a stage fails?** The orchestrator exits immediately with the stage name; later stages never run.
49. **How do you prove individual contribution?** Separate branches, PRs with reviews, `git shortlog -sn`, GitHub Contributors graph - all from real commits.
50. **Biggest limitations?** Synthetic small data, one machine, single NameNode, Spark local mode, no security/HA, no performance benchmarks across cluster sizes.

## Hard follow-ups
* *"Why Hive if Spark can do everything?"* Hive gives a shared, persistent catalog and SQL access for any engine/user; Spark is the compute engine on top.
* *"What if the metastore is lost?"* Data is safe in HDFS; tables must be re-created (external tables + `MSCK`) - which is why DDL is scripted.
* *"How would you scale this?"* Real multi-node HDFS, YARN/K8s Spark, ORC/Parquet instead of CSV, bucketing/compression, HA NameNode and metastore.
* *"Why CSV?"* Simple to inspect and explain; columnar formats (Parquet/ORC) would be far faster in production.
