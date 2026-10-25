"""Data cleaning and validation (Member 1).

Reads the raw CSV, rejects invalid rows (with a reason), standardises text and
dates, recomputes sales_amount = quantity * unit_price and writes:
  data/retail_sales.csv        cleaned data (9 columns, ISO dates)
  data/rejected_rows.csv       every rejected row + reject_reason
  data/cleaning_report.json    counts per rule

Usage:  python -m src.data.clean_data
"""
import json
import logging
import sys

import pandas as pd

from src.common import (CATEGORIES, CLEAN_CSV, CLEANING_REPORT, COLUMNS, DATE_END, DATE_START,
                        MAX_QUANTITY, MAX_UNIT_PRICE, RAW_CSV, REGIONS, REJECTED_CSV)

log = logging.getLogger("clean")
REQUIRED = ["transaction_id", "sale_date", "region", "store_id", "product_id",
            "category", "quantity", "unit_price"]
DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"]
NULL_TOKENS = {"", "nan", "null", "none", "na", "n/a"}


def _parse_dates(series: pd.Series) -> pd.Series:
    parsed = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    for fmt in DATE_FORMATS:
        parsed = parsed.fillna(pd.to_datetime(series, format=fmt, errors="coerce"))
    return parsed


def clean_dataframe(raw: pd.DataFrame):
    """Return (clean_df, rejected_df, report_dict). Pure function - easy to unit test."""
    missing_cols = [c for c in COLUMNS if c not in raw.columns]
    if missing_cols:
        raise ValueError(f"Input is missing required columns: {missing_cols}")

    df = raw[COLUMNS].copy()
    for c in COLUMNS:
        s = df[c].astype("object").where(df[c].notna(), "").astype(str).str.strip()
        df[c] = s.mask(s.str.lower().isin(NULL_TOKENS), "")
    is_blank = df[REQUIRED].eq("").any(axis=1)

    # ---- standardise text -------------------------------------------------
    region_norm = df["region"].str.title()
    region_lookup = {r.lower(): r for r in REGIONS}
    region_ok = region_norm.str.lower().map(region_lookup)
    cat_lookup = {c.lower(): c for c in CATEGORIES}
    cat_ok = df["category"].str.lower().map(cat_lookup)
    text_standardised = int(((region_ok.notna()) & (region_ok != df["region"])).sum()
                            + ((cat_ok.notna()) & (cat_ok != df["category"])).sum())

    # ---- dates ------------------------------------------------------------
    parsed = _parse_dates(df["sale_date"])
    bad_date = df["sale_date"].ne("") & (parsed.isna() | (parsed < pd.Timestamp(DATE_START))
                                         | (parsed > pd.Timestamp(DATE_END)))
    non_iso_dates = int((df["sale_date"].ne("") & parsed.notna()
                         & (parsed.dt.strftime("%Y-%m-%d") != df["sale_date"])).sum())

    # ---- numbers ----------------------------------------------------------
    qty = pd.to_numeric(df["quantity"], errors="coerce")
    bad_qty = df["quantity"].ne("") & (qty.isna() | (qty <= 0) | (qty % 1 != 0) | (qty > MAX_QUANTITY))
    price = pd.to_numeric(df["unit_price"], errors="coerce")
    bad_price = df["unit_price"].ne("") & (price.isna() | (price <= 0) | (price > MAX_UNIT_PRICE))

    reason = pd.Series("", index=df.index)
    rules = [
        ("missing_value", is_blank),
        ("unexpected_region", region_ok.isna() & df["region"].ne("")),
        ("unexpected_category", cat_ok.isna() & df["category"].ne("")),
        ("invalid_date", bad_date),
        ("invalid_quantity", bad_qty),
        ("invalid_price", bad_price),
    ]
    for name, mask in rules:  # first failing rule wins
        reason = reason.mask(reason.eq("") & mask.fillna(False).astype(bool), name)

    # ---- duplicates (only among otherwise valid rows; keep first) ---------
    valid = reason.eq("")
    dup_mask = valid & df["transaction_id"].where(valid).duplicated(keep="first") & df["transaction_id"].ne("")
    reason = reason.mask(dup_mask, "duplicate_transaction_id")

    ok = reason.eq("")
    out = pd.DataFrame({
        "transaction_id": df["transaction_id"], "sale_date": parsed.dt.strftime("%Y-%m-%d"),
        "region": region_ok, "store_id": df["store_id"].str.upper(), "product_id": df["product_id"].str.upper(),
        "category": cat_ok, "quantity": qty, "unit_price": price.round(2),
    })[ok].copy()
    out["quantity"] = out["quantity"].astype(int)
    expected = (out["quantity"] * out["unit_price"]).round(2)
    raw_amt = pd.to_numeric(df.loc[ok, "sales_amount"], errors="coerce")
    amount_fixed = int(((raw_amt - expected).abs() > 0.005).fillna(True).sum())
    out["sales_amount"] = expected
    out = out[COLUMNS].sort_values("transaction_id").reset_index(drop=True)

    rejected = raw.loc[~ok].copy()
    rejected["reject_reason"] = reason[~ok]
    report = {
        "input_rows": int(len(raw)), "clean_rows": int(len(out)), "rejected_rows": int((~ok).sum()),
        "rejected_by_reason": {k: int(v) for k, v in reason[~ok].value_counts().items()},
        "sales_amount_recomputed": amount_fixed,
        "dates_reformatted_to_iso": non_iso_dates,
        "region_or_category_text_standardised": text_standardised,
    }
    return out, rejected, report


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if not RAW_CSV.exists():
        log.error("Raw file %s not found. Run: python -m src.data.generate_data", RAW_CSV)
        return 1
    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False)
    clean, rejected, report = clean_dataframe(raw)
    if clean.empty:
        log.error("No valid rows after cleaning - refusing to continue.")
        return 1
    clean.to_csv(CLEAN_CSV, index=False, float_format="%.2f")
    rejected.to_csv(REJECTED_CSV, index=False)
    CLEANING_REPORT.write_text(json.dumps(report, indent=2))
    log.info("Cleaning report: %s", json.dumps(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
