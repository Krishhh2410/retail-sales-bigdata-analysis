"""Spark analytics (Member 3). Every number is computed by Spark SQL, not pandas.

Modes
  hive        read retail_dw.sales_partitioned through the Hive metastore (cluster; run inside spark-client)
  local-hive  LOCAL TEST: embedded Derby metastore + local files, same DDL (not HDFS)
Results (small aggregated tables) are brought to the driver only to write CSV files.

Usage:  python -m src.analytics.spark_analysis --mode hive
"""
import argparse
import datetime as dt
import json
import logging
import sys
from pathlib import Path

from src.common import OUTPUT_DIR
from src.analytics.spark_session import build_local_hive_session, build_session

log = logging.getLogger("spark")

SEASON = ("CASE WHEN sales_month IN (12,1,2) THEN 'Winter' WHEN sales_month IN (3,4,5) THEN 'Spring' "
          "WHEN sales_month IN (6,7,8) THEN 'Summer' ELSE 'Autumn' END")
REV = "ROUND(CAST(SUM(sales_amount) AS DOUBLE), 2)"

QUERIES = {
    "overall_metrics": f"SELECT COUNT(*) AS total_transactions, SUM(quantity) AS total_units, {REV} AS total_revenue FROM {{t}}",
    "revenue_by_category": f"SELECT category, SUM(quantity) AS total_units, {REV} AS total_revenue FROM {{t}} GROUP BY category ORDER BY total_revenue DESC, category",
    "revenue_by_region": f"SELECT region, SUM(quantity) AS total_units, {REV} AS total_revenue FROM {{t}} GROUP BY region ORDER BY total_revenue DESC, region",
    "top_10_stores": f"SELECT store_id, region, SUM(quantity) AS total_units, {REV} AS total_revenue FROM {{t}} GROUP BY store_id, region ORDER BY total_revenue DESC, store_id LIMIT 10",
    "top_10_products": f"SELECT product_id, category, SUM(quantity) AS total_units, {REV} AS total_revenue FROM {{t}} GROUP BY product_id, category ORDER BY total_revenue DESC, product_id LIMIT 10",
    "monthly_revenue": f"SELECT sales_year, sales_month, SUM(quantity) AS total_units, {REV} AS total_revenue FROM {{t}} GROUP BY sales_year, sales_month ORDER BY sales_year, sales_month",
    "yearly_revenue": f"SELECT sales_year, SUM(quantity) AS total_units, {REV} AS total_revenue FROM {{t}} GROUP BY sales_year ORDER BY sales_year",
    "seasonal_revenue": f"SELECT sales_year, {SEASON} AS season, SUM(quantity) AS total_units, {REV} AS total_revenue FROM {{t}} GROUP BY sales_year, {SEASON} ORDER BY sales_year, season",
}

PRUNING_SQL = ("SELECT SUM(sales_amount) FROM {t} "
               "WHERE region = 'West' AND sales_year = 2025 AND sales_month BETWEEN 6 AND 8")


def analyze(spark, table: str, out_dir: Path = OUTPUT_DIR):
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, sql in QUERIES.items():
        pdf = spark.sql(sql.format(t=table)).toPandas()
        pdf.to_csv(out_dir / f"{name}.csv", index=False)
        log.info("%-20s -> %d rows", name, len(pdf))
    # optional year-over-year by month (uses the monthly result computed above by Spark)
    yoy = spark.sql(f"""
        SELECT sales_month,
               {REV.replace('SUM(sales_amount)', 'SUM(CASE WHEN sales_year = (SELECT MIN(sales_year) FROM ' + table + ') THEN sales_amount END)')} AS revenue_first_year,
               {REV.replace('SUM(sales_amount)', 'SUM(CASE WHEN sales_year = (SELECT MAX(sales_year) FROM ' + table + ') THEN sales_amount END)')} AS revenue_last_year
        FROM {table} GROUP BY sales_month ORDER BY sales_month""").toPandas()
    yoy["yoy_growth_pct"] = ((yoy["revenue_last_year"] / yoy["revenue_first_year"] - 1) * 100).round(2)
    yoy.to_csv(out_dir / "yoy_monthly.csv", index=False)


def pruning_demo(spark, table: str, out_dir: Path = OUTPUT_DIR):
    """Capture the physical plan to show partition pruning (PartitionFilters / PartitionCount)."""
    plan = "\n".join(r[0] for r in spark.sql("EXPLAIN FORMATTED " + PRUNING_SQL.format(t=table)).collect())
    res = spark.sql(PRUNING_SQL.format(t=table)).collect()[0][0]
    total = spark.sql(f"SHOW PARTITIONS {table}").count()
    scanned = spark.sql(f"SELECT COUNT(DISTINCT region, sales_year, sales_month) FROM {table} "
                        "WHERE region = 'West' AND sales_year = 2025 AND sales_month BETWEEN 6 AND 8").collect()[0][0]
    text = (f"Query: {PRUNING_SQL.format(t=table)}\nResult: {res}\n"
            f"Registered partitions: {total}; partitions containing the filtered data: {scanned}\n\n{plan}\n")
    (out_dir / "partition_pruning_plan.txt").write_text(text)
    log.info("Partition pruning: %s of %s partitions match the filter", scanned, total)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["hive", "local-hive"], default="hive")
    ap.add_argument("--database", default="retail_dw")
    ap.add_argument("--table", default="sales_partitioned")
    ap.add_argument("--out", default=str(OUTPUT_DIR))
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out = Path(args.out)
    try:
        spark = build_local_hive_session() if args.mode == "local-hive" else build_session(hive=True)
        table = f"{args.database}.{args.table}"
        if spark.conf.get("spark.sql.catalogImplementation") != "hive":
            raise RuntimeError("Spark session is not using the Hive catalog")
        if not spark.catalog.tableExists(table):
            raise RuntimeError(f"Hive table {table} not found - run the Hive workflow first")
        analyze(spark, table, out)
        pruning_demo(spark, table, out)
        info = {"mode": args.mode, "spark_version": spark.version, "source_table": table,
                "catalog": spark.conf.get("spark.sql.catalogImplementation"),
                "master": spark.sparkContext.master,
                "metastore_uris": spark.sparkContext._jsc.hadoopConfiguration().get("hive.metastore.uris"),
                "default_fs": spark.sparkContext._jsc.hadoopConfiguration().get("fs.defaultFS"),
                "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        (out / "spark_run_info.json").write_text(json.dumps(info, indent=2))
        log.info("Spark run info: %s", info)
        spark.stop()
        return 0
    except Exception as exc:  # fail loudly so the pipeline stops
        log.error("Spark analytics failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
