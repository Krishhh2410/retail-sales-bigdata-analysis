"""Shared constants so Python, HDFS, Hive and Spark all agree on one schema."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_CSV = DATA_DIR / "retail_sales_raw.csv"
CLEAN_CSV = DATA_DIR / "retail_sales.csv"
REJECTED_CSV = DATA_DIR / "rejected_rows.csv"
CLEANING_REPORT = DATA_DIR / "cleaning_report.json"
OUTPUT_DIR = ROOT / "outputs"
WAREHOUSE_DIR = OUTPUT_DIR / "warehouse"  # partition tree that gets uploaded to HDFS
SQL_DIR = ROOT / "sql"

# Column order of the cleaned CSV (also the order of the Hive staging table).
COLUMNS = [
    "transaction_id", "sale_date", "region", "store_id", "product_id",
    "category", "quantity", "unit_price", "sales_amount",
]
# Hive partition columns. region is stored in the directory name, so the
# partition files do NOT contain the region column.
PARTITION_COLUMNS = ["region", "sales_year", "sales_month"]
DATA_COLUMNS = [c for c in COLUMNS if c != "region"]

REGIONS = ["North", "South", "East", "West", "Central"]
CATEGORIES = ["Electronics", "Grocery", "Clothing", "Home & Kitchen", "Beauty", "Sports"]

DATE_START = "2024-01-01"
DATE_END = "2025-12-31"
MAX_QUANTITY = 1000
MAX_UNIT_PRICE = 100000.0

# HDFS layout (the same layout is used in the Hive DDL via ${hivevar:DATA_ROOT}).
HDFS_ROOT = "/retail"
HDFS_STAGING = f"{HDFS_ROOT}/staging"
HDFS_WAREHOUSE = f"{HDFS_ROOT}/warehouse/sales"


def partition_path(region: str, year: int, month: int) -> str:
    """Hive-style partition directory, e.g. region=West/sales_year=2025/sales_month=1"""
    return f"region={region}/sales_year={int(year)}/sales_month={int(month)}"
