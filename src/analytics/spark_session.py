"""Spark session helpers + a tiny SQL-file runner (Member 3, with Member 2's SQL)."""
import os
import re
import shutil
import sys
from pathlib import Path

# Ensure Spark workers use the exact active Python interpreter (prevents Windows python alias issue)
os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

from pyspark.sql import SparkSession

from src.common import SQL_DIR, WAREHOUSE_DIR, CLEAN_CSV, OUTPUT_DIR


def build_session(app_name="retail-sales-analytics", hive=True, master=None, extra=None):
    b = SparkSession.builder.appName(app_name).config("spark.sql.shuffle.partitions", "8") \
        .config("spark.ui.showConsoleProgress", "false")
    if master:
        b = b.master(master)
    for k, v in (extra or {}).items():
        b = b.config(k, v)
    if hive:
        b = b.enableHiveSupport()  # uses hive-site.xml (metastore URI) from SPARK_CONF_DIR on the cluster
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark


def split_statements(sql_text: str):
    lines = [ln for ln in sql_text.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def run_sql_file(spark, path: Path, variables=None):
    """Run every statement of a .sql file; ${hivevar:NAME} placeholders are substituted."""
    text = Path(path).read_text()
    for k, v in (variables or {}).items():
        text = text.replace("${hivevar:%s}" % k, v)
    results = []
    for stmt in split_statements(text):
        results.append(spark.sql(stmt))
    return results


LOCAL_ROOT = OUTPUT_DIR / "_local_hive"


def build_local_hive_session(root: Path = LOCAL_ROOT):
    """LOCAL TEST MODE: Spark + embedded Derby Hive metastore + local filesystem.
    Same DDL as the cluster, but NOT HDFS and NOT HiveServer2. Rebuilt from scratch each run."""
    if root.exists():
        shutil.rmtree(root)
    (root / "data" / "staging").mkdir(parents=True)
    shutil.copy(CLEAN_CSV, root / "data" / "staging" / "retail_sales.csv")
    shutil.copytree(WAREHOUSE_DIR, root / "data" / "warehouse" / "sales")
    spark = build_session(
        "retail-local-hive", hive=True, master="local[*]",
        extra={"spark.sql.warehouse.dir": str(root / "spark-warehouse"),
               "spark.hadoop.javax.jdo.option.ConnectionURL":
                   f"jdbc:derby:;databaseName={root / 'metastore_db'};create=true"})
    data_root = (root / "data").resolve().as_uri()
    for f in ("01_create_database.sql", "02_create_tables.sql", "03_create_partitions.sql"):
        run_sql_file(spark, SQL_DIR / f, {"DATA_ROOT": data_root})
    return spark
