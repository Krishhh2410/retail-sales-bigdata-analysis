"""Deterministic SYNTHETIC retail data generator (Member 1).

All records are synthetic - they are NOT real business transactions.
A fixed seed makes the output identical on every machine. A small share of rows
is deliberately corrupted so the cleaning step has something real to do.

Usage:  python -m src.data.generate_data [--rows 50000] [--seed 42]
"""
import argparse
import csv
import datetime as dt
import logging
import random

from src.common import (CATEGORIES, COLUMNS, DATE_END, DATE_START, RAW_CSV, REGIONS)

log = logging.getLogger("generate")

STORE_REGION = {f"S{i:02d}": REGIONS[(i - 1) // 4] for i in range(1, 21)}  # 20 stores, 4/region
CATEGORY_SPEC = {  # (min price, max price, max quantity)
    "Electronics": (35, 900, 3), "Grocery": (1, 15, 10), "Clothing": (10, 120, 4),
    "Home & Kitchen": (8, 250, 4), "Beauty": (4, 80, 5), "Sports": (12, 300, 3),
}
PRODUCTS_PER_CATEGORY = 7
MONTH_FACTOR = {1: .85, 2: .8, 3: .9, 4: .95, 5: 1.0, 6: 1.05, 7: 1.0, 8: 1.0,
                9: .95, 10: 1.05, 11: 1.3, 12: 1.5}
GROWTH_2025 = 1.12


def category_weight(category: str, month: int) -> float:
    """Simple seasonality so the trend/seasonal reports show something."""
    w = 1.0
    if category == "Electronics" and month in (11, 12): w = 1.8
    if category == "Sports" and month in (6, 7, 8): w = 1.5
    if category == "Clothing" and month in (11, 12): w = 1.3
    if category == "Clothing" and month in (3, 4): w = 1.2
    if category == "Grocery" and month == 12: w = 1.3
    if category == "Beauty" and month in (5, 12): w = 1.25
    if category == "Home & Kitchen" and month == 11: w = 1.3
    return w


def build_catalog(rng):
    catalog, n = {}, 1
    for cat in CATEGORIES:
        lo, hi, _ = CATEGORY_SPEC[cat]
        catalog[cat] = []
        for _ in range(PRODUCTS_PER_CATEGORY):
            catalog[cat].append((f"P{n:03d}", round(rng.uniform(lo, hi), 2)))
            n += 1
    return catalog


def generate_clean_rows(n_rows: int, seed: int):
    rng = random.Random(seed)
    catalog = build_catalog(rng)
    stores = sorted(STORE_REGION)
    store_w = [rng.uniform(0.6, 1.4) for _ in stores]
    start, end = dt.date.fromisoformat(DATE_START), dt.date.fromisoformat(DATE_END)
    days = [start + dt.timedelta(d) for d in range((end - start).days + 1)]
    day_w = [MONTH_FACTOR[d.month] * (GROWTH_2025 if d.year == 2025 else 1.0) for d in days]
    chosen_days = rng.choices(days, weights=day_w, k=n_rows)
    rows = []
    for i, day in enumerate(chosen_days, start=1):
        store = rng.choices(stores, weights=store_w)[0]
        cat = rng.choices(CATEGORIES, weights=[category_weight(c, day.month) for c in CATEGORIES])[0]
        pid, base = rng.choice(catalog[cat])
        max_q = CATEGORY_SPEC[cat][2]
        qty = rng.choices(range(1, max_q + 1), weights=[max_q - q + 1 for q in range(1, max_q + 1)])[0]
        price = round(base * rng.choice([1.0, 1.0, 1.0, 0.9, 0.95, 1.05]), 2)
        rows.append({
            "transaction_id": f"T{i:08d}", "sale_date": day.isoformat(),
            "region": STORE_REGION[store], "store_id": store, "product_id": pid,
            "category": cat, "quantity": str(qty), "unit_price": f"{price:.2f}",
            "sales_amount": f"{qty * price:.2f}",
        })
    return rows


def inject_issues(rows, rng):
    """Corrupt a known number of rows. Returns a dict describing what was injected."""
    n = len(rows)
    dups = [dict(rows[i]) for i in rng.sample(range(n), 150)]  # copies taken before corruption
    plan = [("missing", 100), ("bad_date", 80), ("slash_date", 100), ("bad_qty", 120),
            ("bad_price", 60), ("wrong_amount", 100), ("bad_category", 50),
            ("bad_region", 50), ("messy_region", 150)]
    idx = rng.sample(range(n), sum(c for _, c in plan))
    pos = 0
    for kind, count in plan:
        for i in idx[pos:pos + count]:
            r = rows[i]
            if kind == "missing":
                r[rng.choice(["sale_date", "region", "store_id", "product_id", "category",
                              "quantity", "unit_price"])] = ""
            elif kind == "bad_date":
                r["sale_date"] = rng.choice(["2024-13-45", "not_a_date", "2025-02-30", "31/31/2024"])
            elif kind == "slash_date":
                r["sale_date"] = r["sale_date"].replace("-", "/")
            elif kind == "bad_qty":
                r["quantity"] = rng.choice(["-3", "0", "abc", "2.5"])
            elif kind == "bad_price":
                r["unit_price"] = rng.choice(["0", "-4.99", "abc"])
            elif kind == "wrong_amount":
                r["sales_amount"] = f"{float(r['sales_amount']) + rng.uniform(1, 50):.2f}"
            elif kind == "bad_category":
                r["category"] = "Misc"
            elif kind == "bad_region":
                r["region"] = "Mars"
            elif kind == "messy_region":
                r["region"] = rng.choice([f"  {r['region'].lower()} ", r["region"].upper()])
        pos += count
    rows.extend(dups)  # duplicates appended after the originals
    return dict(plan, duplicates=len(dups))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows", type=int, default=50000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(RAW_CSV))
    ap.add_argument("--no-issues", action="store_true", help="write a perfectly clean file")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rows = generate_clean_rows(args.rows, args.seed)
    injected = {} if args.no_issues else inject_issues(rows, random.Random(args.seed + 1))
    RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    log.info("Wrote %d SYNTHETIC rows to %s (seed=%d). Injected issues: %s",
             len(rows), args.out, args.seed, injected)


if __name__ == "__main__":
    main()
