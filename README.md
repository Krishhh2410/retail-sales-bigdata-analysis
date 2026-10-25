# Retail Sales Data Warehouse Analysis (BDS project)

HDFS + Hive + Spark pipeline over a **synthetic** retail dataset: clean in Python -> store in HDFS -> Hive external tables partitioned by `region/sales_year/sales_month` -> Spark SQL analytics -> CSV reports, charts, insights.

> **Read `docs/STATUS.md` first.** It lists exactly what was executed and tested and what is still unverified (the Docker/HDFS/HiveServer2 cluster has *not* been run by the authoring tool - you must run and screenshot it).

## Quick start (no Docker): local mode
Needs Python 3.10+ and Java 8/11/17/21 (`java -version`).
```bash
pip install -r requirements.txt
python -m src.pipeline.run_pipeline --mode local     # ~2 minutes
python -m pytest -q
```
Local mode runs real Spark SQL with Hive support (embedded Derby metastore, local files, same DDL). It is **not** HDFS and **not** HiveServer2.

## Cluster mode (Docker Desktop, 8 GB RAM recommended)
```bash
docker compose up -d --build
python -m src.pipeline.run_pipeline --mode cluster     # run from Git Bash / WSL / Linux / macOS
```
HDFS UI: http://localhost:50070 - HiveServer2: `jdbc:hive2://localhost:10000`. Full steps: `docs/setup_guide.md`.

## Layout
`src/data` (generate, clean, partitions) - `src/hdfs` (upload/verify) - `src/hive` (workflow) - `src/analytics` (Spark, charts, insights, pandas oracle) - `src/pipeline` (orchestrator, validator) - `sql/` - `tests/` - `docs/` - `outputs/` (generated reports/charts).

## Documents
`docs/PROJECT_EXPLANATION.md` (complete viva & project guide), `PROJECT_REPORT.md`, `PRESENTATION_OUTLINE.md`, `docs/architecture.md`, `docs/data_dictionary.md`, `docs/setup_guide.md`, `docs/github_workflow.md`, `docs/team_contributions.md`, `docs/test_plan.md`, `docs/screenshots_checklist.md`, `docs/viva_questions.md`, `docs/STATUS.md`.

## Team
| Member | Module | Branch |
|---|---|---|
| Krish Patel | Dataset, cleaning, HDFS | `feature/data-hdfs` |
| Bhavya Kalariya | Hive warehouse + SQL + orchestration | `feature/hive-warehouse` |
| Jainam Kamdar | Spark analytics, charts, validation | `feature/spark-analytics` |
