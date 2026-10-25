# Retail Sales Data Warehouse Analysis
**Subject:** Big Data Systems (BDS) | **Institution:** [INSTITUTION] | **Faculty:** [FACULTY NAME] | **Academic year:** [YEAR]
| Member | Roll/ID | Module |
|---|---|---|
| Krish Patel | [ID] | Dataset, cleaning, HDFS |
| Bhavya Kalariya | [ID] | Hive warehouse, orchestration |
| Jainam Kamdar | [ID] | Spark analytics, visualization |

> Results below were produced by the repository's own pipeline in **local mode** (Spark 3.5.3 with Hive support, embedded Derby metastore, local filesystem). The numbers depend only on the deterministic synthetic dataset, so they must be identical on the cluster; replace/confirm them with your cluster run and add screenshots where marked **[SCREENSHOT]**.

## 1. Abstract
We build a retail sales data warehouse using Hadoop HDFS, Apache Hive and Apache Spark. A deterministic synthetic dataset (50,150 raw rows) is cleaned in Python (49,540 valid rows), stored in HDFS, exposed as Hive external tables partitioned by region, year and month, and analysed with Spark SQL. The pipeline produces revenue reports, charts and validated insights, and is orchestrated by a single script that stops on failure.

## 2. Introduction
Retailers generate large volumes of transactions. Distributed storage (HDFS), a SQL warehouse layer (Hive) and an in-memory engine (Spark) allow such data to be stored cheaply and analysed at scale.

## 3. Problem statement
Design and implement a reproducible pipeline that stores retail transactions in a distributed file system, organises them as a partitioned warehouse, and computes sales analytics with a distributed engine.

## 4. Motivation
Single-machine tools do not scale and offer no fault tolerance; partitioning reduces scanned data; learning the Hadoop ecosystem integration (HDFS - metastore - Spark) is the core BDS skill.

## 5. Objectives
Dataset and validation; HDFS storage with 3 DataNodes; Hive database/tables partitioned by region/year/month; Hive and Spark aggregations; CSV reports and charts; cross-stage validation; GitHub collaboration; documentation and viva preparation.

## 6. Existing system and limitations
Spreadsheet/single-database analysis: limited size, no replication, no partition-based skipping, hard to reproduce.

## 7. Proposed system
HDFS -> Hive external tables + metastore -> Spark SQL -> CSV/charts, automated by `run_pipeline.py` with validation.

## 8. Technology stack
Hadoop HDFS 2.7.4 (Docker), Hive 2.3.2 + PostgreSQL metastore, Spark/PySpark 3.5.3, Python 3 (pandas, matplotlib), SQL/HiveQL, Docker Compose, Git/GitHub.

## 9. System architecture
See `docs/architecture.md` and `diagrams/architecture.mmd`. **Honest scope:** 1 NameNode + 3 DataNodes in containers on one host; Spark runs `local[*]` in a client container. This is not a three-worker-node cluster.

## 10. Dataset description
Synthetic (seed 42): 2024-01-01..2025-12-31, 5 regions, 20 stores, 6 categories, 42 products; schema in `docs/data_dictionary.md`. Not real business data.

## 11. Data preprocessing
Raw 50,150 rows -> 49,540 clean, 610 rejected: duplicates 150, invalid quantity 120, missing values 100, invalid dates 80, invalid price 60, unexpected category 50, unexpected region 50. Also: 100 `sales_amount` values recomputed, 100 dates reformatted to ISO, 150 region texts standardised.

## 12. HDFS architecture and storage
Paths `/retail/staging/retail_sales.csv` and `/retail/warehouse/sales/region=*/sales_year=*/sales_month=*/part-00000.csv`; replication factor 3. **[SCREENSHOT: NameNode UI with 3 DataNodes; fsck output]** Measured cluster results: [TO FILL after cluster run].

## 13. Hive warehouse schema
Database `retail_dw`; `staging_sales` (9 columns, external, header skipped) and `sales_partitioned` (8 data columns + partition columns `region`, `sales_year`, `sales_month`). DDL in `sql/02_create_tables.sql`.

## 14. Partitioning strategy
120 partitions (5 regions x 2 years x 12 months). Layout `region=West/sales_year=2025/sales_month=1`. Registered with `MSCK REPAIR TABLE`. Measured: filter `West, 2025, months 6-8` matches 3 of 120 partitions (`outputs/partition_pruning_plan.txt`).

## 15. SQL queries
`sql/04_analysis_queries.sql` (revenue, units, category, region, top-10 stores/products, monthly, yearly, seasonal, region+date range, EXPLAIN) and `sql/05_validation_queries.sql`.

## 16. Spark implementation
`src/analytics/spark_analysis.py`: `enableHiveSupport()`, reads `retail_dw.sales_partitioned`, Spark SQL aggregations, writes CSV. Spark and Hive share the metastore and HDFS files.

## 17. Experimental setup
Local-mode results: Linux sandbox, Java 21, PySpark 3.5.3. Cluster: Docker Desktop [CPU/RAM], images per `docker-compose.yml` **[FILL]**.

## 18. Testing methodology
29 pytest tests; 31 pipeline validation checks; cross-checks cleaned CSV = partition files = Spark (= Hive on cluster). See `docs/test_plan.md`.

## 19. Actual results
* Total: 49,540 transactions, 111,486 units, revenue **13,229,178.90**.
* By category: Electronics 6,751,807.71 (51.0%), Sports 2,640,699.76, Home & Kitchen 1,563,397.39, Clothing 1,104,767.11, Beauty 1,048,105.00, Grocery 120,401.93.
* By region: West 2,966,714.77; Central 2,948,633.77; East 2,647,925.19; South 2,459,783.03; North 2,206,122.14.
* Top stores: S19 (Central) 963,532.78; S12 (East) 934,913.28; S16 (West) 824,664.37. Top products: P007 1,710,411.05; P005 1,430,258.40; P006 1,248,797.40 (all Electronics).
* Yearly: 2024 6,273,268.44; 2025 6,955,910.46 (+10.9%). Peak month 2025-12 (911,773.24); lowest 2024-02 (359,140.32).
* Seasonal 2025: Autumn 1,902,705.31 > Winter 1,788,008.76 > Summer 1,714,383.87 > Spring 1,550,812.52.
Charts: `outputs/charts/*.png` **[INSERT]**. Insights: `outputs/business_insights.md`. These patterns are artefacts of the synthetic generator, not real retail behaviour.

## 20. Performance observations
Local-mode stage timings (this sandbox, one run): see `outputs/pipeline_timings.json` (Spark stage ~76 s, dominated by JVM start-up and 8 queries on one machine). No cluster-vs-single-node speed-up was measured, so none is claimed. [Add your own cluster timings if measured.]

## 21. Limitations
Synthetic small data; one host; single NameNode; Spark local mode; CSV not columnar; no security; Hive on MapReduce is slow; Spark ignores Hive header-skip property (observed).

## 22. Future enhancements
Parquet/ORC, real multi-node cluster, YARN/Kubernetes Spark, HA NameNode, streaming ingestion, real public dataset, dashboard (Superset/Power BI).

## 23. Conclusion
The project delivers a coherent, validated HDFS -> Hive -> Spark pipeline with partitioned storage and reproducible analytics; cluster integration steps are scripted and must be confirmed on the team's machines.

## 24. References
Apache Hadoop, Hive and Spark documentation; `bde2020/docker-hive` project; [ADD course material and textbooks].

## 25. Individual contributions
See `docs/team_contributions.md`; attach GitHub contributor screenshots **[SCREENSHOT]**.
