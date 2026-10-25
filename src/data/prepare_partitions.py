"""Write the cleaned CSV as a Hive-style partition tree (Member 1 -> Member 2 hand-off).

outputs/warehouse/region=West/sales_year=2025/sales_month=1/part-00000.csv
Files contain only the non-partition columns (no header, no region) because
Hive reads partition values from the directory names.
Safe to re-run: the target tree is deleted and rebuilt.
"""
import logging
import shutil
import sys

import pandas as pd

from src.common import CLEAN_CSV, DATA_COLUMNS, WAREHOUSE_DIR, partition_path

log = logging.getLogger("partitions")


def build_partitions(clean_csv=CLEAN_CSV, out_dir=WAREHOUSE_DIR) -> int:
    df = pd.read_csv(clean_csv, dtype=str, keep_default_na=False)  # strings keep 2-decimal formatting
    year = df["sale_date"].str[:4].astype(int)
    month = df["sale_date"].str[5:7].astype(int)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    n = 0
    for (region, y, m), g in df.groupby([df["region"], year, month]):
        d = out_dir / partition_path(region, y, m)
        d.mkdir(parents=True, exist_ok=True)
        g[DATA_COLUMNS].to_csv(d / "part-00000.csv", header=False, index=False)
        n += 1
    log.info("Wrote %d partitions (%d rows) under %s", n, len(df), out_dir)
    return n


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not CLEAN_CSV.exists():
        log.error("%s not found. Run the cleaning step first.", CLEAN_CSV)
        return 1
    return 0 if build_partitions() > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
