"""pandas reference implementation - LOCAL TESTING ONLY.

This is NOT Spark. It exists so unit tests and the validator have an independent
"oracle" to compare Spark results against. Never present its output as Spark execution.
"""
import pandas as pd


def season_of(month: int) -> str:
    if month in (12, 1, 2): return "Winter"
    if month in (3, 4, 5): return "Spring"
    if month in (6, 7, 8): return "Summer"
    return "Autumn"


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["sales_year"] = d["sale_date"].astype(str).str[:4].astype(int)
    d["sales_month"] = d["sale_date"].astype(str).str[5:7].astype(int)
    return d


def _agg(d, keys):
    return (d.groupby(keys, as_index=False)
             .agg(total_units=("quantity", "sum"), total_revenue=("sales_amount", "sum")))


def overall(df):
    return pd.DataFrame([{"total_transactions": len(df), "total_units": int(df["quantity"].sum()),
                          "total_revenue": round(float(df["sales_amount"].sum()), 2)}])


def by_category(df):
    return _agg(df, ["category"]).sort_values(["total_revenue", "category"], ascending=[False, True]).reset_index(drop=True)


def by_region(df):
    return _agg(df, ["region"]).sort_values(["total_revenue", "region"], ascending=[False, True]).reset_index(drop=True)


def top_stores(df, n=10):
    r = _agg(df, ["store_id", "region"])
    return r.sort_values(["total_revenue", "store_id"], ascending=[False, True]).head(n).reset_index(drop=True)


def top_products(df, n=10):
    r = _agg(df, ["product_id", "category"])
    return r.sort_values(["total_revenue", "product_id"], ascending=[False, True]).head(n).reset_index(drop=True)


def monthly(df):
    return _agg(_prep(df), ["sales_year", "sales_month"]).sort_values(["sales_year", "sales_month"]).reset_index(drop=True)


def yearly(df):
    return _agg(_prep(df), ["sales_year"]).sort_values("sales_year").reset_index(drop=True)


def seasonal(df):
    d = _prep(df)
    d["season"] = d["sales_month"].map(season_of)
    return _agg(d, ["sales_year", "season"]).sort_values(["sales_year", "season"]).reset_index(drop=True)
