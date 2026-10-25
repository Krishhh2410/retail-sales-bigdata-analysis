"""Final validation: cleaned data vs partitions vs Spark vs (optionally) Hive vs reports.

Exit code 0 only if every check passes. Use --require-hive on the cluster so a missing
Hive export counts as a failure.
"""
import argparse
import json
import math
import sys

import pandas as pd

from src.common import CLEAN_CSV, CLEANING_REPORT, COLUMNS, OUTPUT_DIR, RAW_CSV, WAREHOUSE_DIR

TOL = 0.01  # absolute tolerance for money totals (sums of 2-decimal values)
CSV_REPORTS = ["overall_metrics", "revenue_by_category", "revenue_by_region", "top_10_stores",
               "top_10_products", "monthly_revenue", "yearly_revenue", "seasonal_revenue", "yoy_monthly"]
CHARTS = ["revenue_by_category", "revenue_by_region", "top_10_stores", "top_10_products",
          "monthly_revenue_trend", "seasonal_comparison"]


def close(a, b):
    return math.isclose(float(a), float(b), abs_tol=TOL, rel_tol=1e-9)


def run_checks(require_hive=False, out=OUTPUT_DIR):
    res = []
    add = lambda name, ok, detail="": res.append((name, bool(ok), detail))
    clean = pd.read_csv(CLEAN_CSV, dtype={"transaction_id": str})
    rep = json.loads(CLEANING_REPORT.read_text())
    raw_rows = sum(1 for _ in open(RAW_CSV, encoding="utf-8")) - 1 if RAW_CSV.exists() else None
    add("columns match schema", list(clean.columns) == COLUMNS)
    add("raw rows = clean + rejected", raw_rows in (None, rep["clean_rows"] + rep["rejected_rows"]),
        f"raw={raw_rows} clean={rep['clean_rows']} rejected={rep['rejected_rows']}")
    add("clean row count = report", len(clean) == rep["clean_rows"])
    add("no duplicate transaction_id", clean["transaction_id"].is_unique)
    add("no null values", int(clean.isna().sum().sum()) == 0)
    add("sales_amount = quantity*unit_price", bool(((clean["quantity"] * clean["unit_price"] - clean["sales_amount"]).abs() <= TOL).all()))
    n_rows, units, rev = len(clean), int(clean["quantity"].sum()), float(clean["sales_amount"].sum())

    part_rows = sum(sum(1 for _ in open(p, encoding="utf-8")) for p in WAREHOUSE_DIR.rglob("*.csv")) if WAREHOUSE_DIR.exists() else -1
    add("partition files hold every clean row", part_rows == n_rows, f"partition rows={part_rows}")

    f = out / "overall_metrics.csv"
    if f.exists():
        s = pd.read_csv(f).iloc[0]
        add("Spark rows = cleaned rows", int(s["total_transactions"]) == n_rows, f"spark={int(s['total_transactions'])} clean={n_rows}")
        add("Spark units = cleaned units", int(s["total_units"]) == units)
        add("Spark revenue ~ cleaned revenue", close(s["total_revenue"], rev), f"spark={s['total_revenue']} clean={rev:.2f}")
    else:
        add("Spark overall_metrics.csv exists", False)
    for name, key in (("revenue_by_category", None), ("revenue_by_region", None), ("monthly_revenue", None), ("yearly_revenue", None)):
        p = out / f"{name}.csv"
        add(f"{name} sums to total revenue", p.exists() and close(pd.read_csv(p)["total_revenue"].sum(), rev))
    hv = out / "hive_totals.csv"
    if hv.exists():
        h = pd.read_csv(hv).iloc[0]
        add("Hive rows = cleaned rows", int(h["row_count"]) == n_rows)
        add("Hive units = cleaned units", int(h["total_units"]) == units)
        add("Hive revenue ~ Spark revenue", close(h["total_revenue"], pd.read_csv(f).iloc[0]["total_revenue"]) if f.exists() else False)
    else:
        add("Hive totals compared", not require_hive, "hive_totals.csv not found" + (" (REQUIRED)" if require_hive else " (skipped: local mode)"))
    for n in CSV_REPORTS:
        add(f"report exists: {n}.csv", (out / f"{n}.csv").exists())
    for n in CHARTS:
        add(f"chart exists: {n}.png", (out / "charts" / f"{n}.png").exists())
    add("business_insights.md exists", (out / "business_insights.md").exists())
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-hive", action="store_true")
    args = ap.parse_args(argv)
    res = run_checks(args.require_hive)
    for name, ok, detail in res:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    failed = [r for r in res if not r[1]]
    print(f"\n{len(res) - len(failed)}/{len(res)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
