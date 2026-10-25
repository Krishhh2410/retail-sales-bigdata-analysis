# Retail Sales Data Warehouse (BDS Project)
## Complete End-to-End Project Explanation & Viva Guide

---

## 1. Executive Summary (The 30-Second Elevator Pitch)
> **If faculty asks: *"What is your project about?"***
>
> *"Our project designs and implements an end-to-end **Big Data Analytics Pipeline** for a retail enterprise. We ingest raw, imperfect transaction data, clean and validate it in **Python**, store it with 3x replication across a distributed **Hadoop HDFS** cluster, organize it into a partitioned data warehouse using **Apache Hive**, and execute distributed in-memory aggregations using **Apache Spark SQL**. The pipeline produces revenue reports and visual dashboards, and automatically executes a 33-point mathematical cross-check to guarantee zero data loss between HDFS, Hive, and Spark."*

---

## 2. Why Big Data Architecture? (Problem Statement & Motivation)
> **If faculty asks: *"Why not use a standard MySQL database or Excel?"***

1. **Volume & Horizontal Scalability:** Single-node relational databases fail when datasets scale to terabytes. HDFS distributes data across commodity worker nodes (DataNodes).
2. **High Availability & Fault Tolerance:** If a hard drive or machine crashes in MySQL, service halts. HDFS uses a default **replication factor of 3**, meaning data exists on three separate nodes simultaneously.
3. **Partition Pruning for Query Performance:** Scanning billions of rows sequentially is slow. By organizing data into a hierarchical directory structure (`region=*/sales_year=*/sales_month=*`), query engines scan only the specific directories requested by a query and skip 95%+ of irrelevant data.
4. **In-Memory Distributed Processing:** While traditional databases rely on disk I/O, **Apache Spark** leverages in-memory caching and Directed Acyclic Graph (DAG) query optimization to perform aggregations 10x–100x faster than traditional MapReduce.

---

## 3. High-Level System Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │ Raw Retail CSV (50,150 synthetic records)    │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 1. Python Cleaning & Preprocessing           │
                    │    - Validates data types & business rules   │
                    │    - Quarantines 610 invalid records         │
                    │    - Yields 49,540 verified records          │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 2. Partition Tree Generation                 │
                    │    - 120 partition directories               │
                    │    - 5 regions × 2 years × 12 months         │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ 3. Distributed Storage (Hadoop HDFS)         │
                    │    - 1 NameNode (metadata & coordinates)     │
                    │    - 3 DataNodes (blocks & 3x replication)   │
                    │    - Staging: /retail/staging/               │
                    │    - Warehouse: /retail/warehouse/sales/     │
                    └──────────────────────┬───────────────────────┘
                                           │
                         ┌─────────────────┴─────────────────┐
                         ▼                                   ▼
          ┌─────────────────────────────┐     ┌─────────────────────────────┐
          │ 4. Hive Metastore & Server  │     │ 5. Apache Spark SQL Engine  │
          │    - PostgreSQL Metastore   │◄────┤    - Connects via Thrift    │
          │    - External Tables        │     │    - Reads HDFS files       │
          │    - MSCK REPAIR TABLE      │     │    - In-Memory Analytics    │
          └─────────────────────────────┘     └──────────────┬──────────────┘
                                                             │
                                                             ▼
                                              ┌─────────────────────────────┐
                                              │ 6. Reports, Charts & Audit  │
                                              │    - 8 Analytical CSVs      │
                                              │    - 6 Visualization PNGs   │
                                              │    - 33/33 Validation PASS  │
                                              └─────────────────────────────┘
```

---

## 4. Detailed Component Walkthrough

### Stage 1: Data Ingestion, Cleaning & Validation (`src/data/`)
* **Raw Input:** 50,150 synthetic transactions spanning 2024–2025 across 5 regions, 20 stores, 6 categories, and 42 products.
* **Injected Anomalies (610 total rejects):**
  - **150 duplicate records** (same transaction ID)
  - **120 invalid quantities** ($\le 0$)
  - **100 records with missing/NULL fields**
  - **80 invalid date formats**
  - **60 invalid prices** ($\le 0$)
  - **50 invalid product categories**
  - **50 invalid store regions**
* **Actions Taken:**
  - Rejected rows are saved to `data/rejected_rows.csv` with specific failure reasons for auditing.
  - Recomputed `sales_amount = quantity * unit_price` to fix rounding/corrupted values.
  - Standardized region text casing and date formats to ISO-8601 (`YYYY-MM-DD`).
* **Output:** Exactly **49,540 clean records** written to `data/retail_sales.csv`.

---

### Stage 2: Partition Tree Organization (`src/data/prepare_partitions.py`)
* Instead of uploading one monolithic CSV, the data is partitioned hierarchically:
  ```
  outputs/warehouse/sales/
     └── region=West/
          └── sales_year=2025/
               └── sales_month=1/
                    └── part-00000.csv
  ```
* **Why 120 partitions?**
  $$\text{5 Regions} \times \text{2 Years (2024, 2025)} \times \text{12 Months} = 120\text{ Partitions}$$
* **Partition Column Handling:** The `region`, `sales_year`, and `sales_month` columns are omitted from `part-00000.csv`. Hive and Spark automatically infer these values from the directory names.

---

### Stage 3: Distributed Storage in Hadoop HDFS (`src/hdfs/`)
* **Storage Cluster Architecture:**
  - **NameNode (Port 50070):** The cluster master. It manages the filesystem namespace, tree hierarchy, and maps blocks to DataNodes. It stores **no raw record data**.
  - **DataNodes (3 instances):** Store the physical data blocks on disk and report health via periodic heartbeats.
* **Storage Locations:**
  - Staging area: `/retail/staging/retail_sales.csv`
  - Warehouse area: `/retail/warehouse/sales/region=*/sales_year=*/sales_month=*`
* **Health & Integrity Verification:**
  - `hdfs dfsadmin -report`: Confirms `Live datanodes (3)`.
  - `hdfs fsck`: Confirms `Default replication factor: 3`, `Average block replication: 3.0`, and file status `HEALTHY`.
  - **MD5 Checksum Verification:** Computed MD5 of local file vs HDFS file (`422a4b51d40a13908d6b90752bf2e00f`) — verified identical.

---

### Stage 4: Apache Hive Data Warehouse (`src/hive/` & `sql/`)
* **Role:** Provides a SQL-like interface (HiveQL) over distributed files stored in HDFS.
* **Hive Metastore:** A dedicated PostgreSQL database storing table metadata (column names, types, storage locations, and registered partitions).
* **External Tables (`CREATE EXTERNAL TABLE`):**
  - **Managed Table:** Dropping the table deletes both schema and underlying HDFS files.
  - **External Table (Used Here):** Dropping the table removes only metadata from PostgreSQL. The HDFS files remain completely safe.
* **Partition Discovery (`MSCK REPAIR TABLE`):**
  - After copying partition folders into HDFS, Hive's metastore must be notified.
  - `MSCK REPAIR TABLE sales_partitioned;` scans HDFS and registers all 120 partition paths into PostgreSQL.

---

### Stage 5: Apache Spark In-Memory Analytics (`src/analytics/`)
* **Why Spark?** Hive 2.x translates queries into MapReduce jobs that write intermediate states to disk. Spark keeps data in-memory (RAM) and optimizes queries using the Catalyst Optimizer, executing queries in seconds.
* **Metastore Sharing (Zero Data Duplication):**
  - Spark is initialized with `enableHiveSupport()`.
  - Spark connects to Hive's metastore via Thrift (`thrift://hive-metastore:9083`).
  - Spark queries the metastore for schema and file locations, then reads directly from HDFS (`hdfs://namenode:8020`). Spark and Hive never copy files to each other.
* **Partition Pruning Demonstrated:**
  - When querying for West region in Summer 2025 (`sales_month IN (6, 7, 8)`), Spark inspects the partition filters and scans only **3 out of 120 partition directories**, ignoring the other 117. Verified in `outputs/partition_pruning_plan.txt`.

---

### Stage 6: Cross-Engine Validation & Reporting (`src/pipeline/validate_outputs.py`)
To ensure total accuracy, an automated validation suite runs **33 mathematical checks**:
1. Schema conformity: Exactly 9 columns with expected names and datatypes.
2. Row conservation: $\text{Raw (50,150)} = \text{Clean (49,540)} + \text{Rejected (610)}$.
3. Data cleanliness: 0 duplicate IDs, 0 NULLs, and `sales_amount == quantity * unit_price` across every row.
4. Cross-engine equality:
   $$\text{Clean CSV Totals} \equiv \text{HDFS Partition Files} \equiv \text{Hive Totals} \equiv \text{Spark Totals}$$
5. Result: **33/33 checks PASS**.

---

## 5. Verified Key Business Results

| Metric | Result |
|---|---|
| **Total Valid Transactions** | 49,540 |
| **Total Quantity Sold** | 111,486 units |
| **Total Net Revenue** | **$13,229,178.90** |
| **Top Performing Category** | Electronics ($6,751,807.71 — 51.0% of total revenue) |
| **Top Performing Region** | West ($2,966,714.77) |
| **Top Revenue Store** | Store S19 in Central ($963,532.78) |
| **Top Product** | P007 ($1,710,411.05 — Electronics) |
| **Year-over-Year (YoY) Growth** | **+10.9%** ($6,273,268.44 in 2024 $\rightarrow$ $6,955,910.46 in 2025) |
| **Peak Sales Month** | December 2025 ($911,773.24) |
| **Lowest Sales Month** | February 2024 ($359,140.32) |

---

## 6. Top Viva Questions & Model Answers

### Q1: *"What is partition pruning and how did you verify it?"*
> **Answer:** *"Partition pruning is an optimization where the query engine uses the `WHERE` clause to identify which partition directories are required and skips scanning the rest. For example, querying West region for June–August 2025 scanned only **3 out of 120 partition directories**. We verified this by checking the Spark physical execution plan recorded in [`outputs/partition_pruning_plan.txt`](file:///c:/Users/bhavy/Downloads/retail-sales-data-warehouse/retail-sales-data-warehouse/outputs/partition_pruning_plan.txt)."*

### Q2: *"What is the difference between Managed and External Hive tables?"*
> **Answer:** *"In a Managed table, Hive owns both metadata and data files; executing `DROP TABLE` deletes the files from HDFS. In an **External table**, Hive only owns the schema in the PostgreSQL metastore; executing `DROP TABLE` deletes only metadata, leaving the raw data in HDFS intact. We use external tables to decouple storage from compute."*

### Q3: *"How do Spark and Hive share data?"*
> **Answer:** *"They share metadata through the Hive Metastore Thrift service (`thrift://hive-metastore:9083`) via `hive-site.xml`. Spark does not query HiveServer2. It asks the metastore for table schemas and HDFS partition paths, and then Spark's own executors read the raw blocks directly from HDFS (`hdfs://namenode:8020`). Data is never duplicated."*

### Q4: *"Why did you partition by region, year, and month?"*
> **Answer:** *"Partitioning by high-cardinality columns (like store or product) creates hundreds of thousands of tiny files. In Hadoop, this causes the **Small Files Problem**, which exhausts NameNode heap memory. Partitioning by 5 regions × 2 years × 12 months produces exactly 120 balanced partitions."*

### Q5: *"Why use DECIMAL(14,2) instead of FLOAT or DOUBLE?"*
> **Answer:** *"Floating-point representations (FLOAT and DOUBLE) suffer from binary rounding errors. For monetary calculations, `DECIMAL(14,2)` provides exact two-decimal precision and avoids accumulated rounding discrepancies."*

### Q6: *"What happens if a DataNode fails in your cluster?"*
> **Answer:** *"Because the replication factor is 3, each block exists on all 3 DataNodes. If one DataNode goes offline, the NameNode detects the missing heartbeat, serves reads from the surviving copies, and automatically re-replicates blocks to maintain replication factor 3."*

### Q7: *"Is your cluster running on multiple physical machines?"*
> **Answer:** *(Be academically honest):*
> *"No, sir/ma'am. We deployed the cluster using **Docker Compose** on a single host. It simulates 1 NameNode container, 3 DataNode containers, a PostgreSQL metastore, HiveServer2, and a Spark client container communicating across an isolated virtual bridge network. It replicates the exact distributed protocols and storage semantics of a production cluster."*

### Q8: *"Why did you use Python for cleaning instead of doing it in Hive/Spark?"*
> **Answer:** *"In production data engineering, raw data from third parties should never be ingested directly into a data lake without schema validation. Ingesting malformed records can corrupt downstream partitioned tables. Validating at the perimeter with Python allows us to isolate bad records in `rejected_rows.csv` before HDFS ingestion."*

---

## 7. Live Demonstration Commands

If your faculty asks you to demonstrate the project live:

### 1. Show Cluster Health
```powershell
docker compose ps
```
*(Shows NameNode, 3 DataNodes, Postgres metastore, and HiveServer2 healthy)*

### 2. Show HDFS NameNode Web Interface
* Open in browser: **http://localhost:50070**
* Navigate to the **Datanodes** tab to show all 3 DataNodes live and reporting.

### 3. Show Hive Table Partitions
```powershell
docker compose exec -T hive-server beeline -u "jdbc:hive2://localhost:10000" -e "USE retail_dw; SHOW PARTITIONS sales_partitioned;"
```
*(Displays all 120 partitions registered)*

### 4. Run the Full Validation Suite
```powershell
python -m src.pipeline.validate_outputs --require-hive
```
*(Displays all 33/33 checks passing)*

### 5. Show Generated Analytical Visualizations
Open the [`outputs/charts/`](file:///c:/Users/bhavy/Downloads/retail-sales-data-warehouse/retail-sales-data-warehouse/outputs/charts/) folder:
- `monthly_revenue_trend.png` (Monthly revenue trajectory)
- `revenue_by_category.png` (Category breakdown with Electronics leading)
- `revenue_by_region.png` (Regional distribution)
- `seasonal_comparison.png` (Seasonal performance comparison)
- `top_10_products.png` and `top_10_stores.png`
