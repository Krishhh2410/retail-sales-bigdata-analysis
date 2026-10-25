"""Charts from the Spark CSV reports (Member 3). Matplotlib only; reads outputs/*.csv."""
import logging
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.common import OUTPUT_DIR

log = logging.getLogger("charts")
CH = OUTPUT_DIR / "charts"


def _bar(df, x, y, title, fname, horizontal=False):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    (ax.barh if horizontal else ax.bar)(df[x].astype(str), df[y] / 1e6 if y == "total_revenue" else df[y], color="#2b6cb0")
    if horizontal: ax.invert_yaxis()
    lab = "Revenue (millions)" if y == "total_revenue" else y
    (ax.set_xlabel if horizontal else ax.set_ylabel)(lab)
    ax.set_title(title)
    if not horizontal: plt.setp(ax.get_xticklabels(), rotation=25, ha="right")
    fig.tight_layout(); fig.savefig(CH / fname, dpi=130); plt.close(fig)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    needed = ["revenue_by_category", "revenue_by_region", "top_10_stores", "top_10_products",
              "monthly_revenue", "seasonal_revenue"]
    missing = [n for n in needed if not (OUTPUT_DIR / f"{n}.csv").exists()]
    if missing:
        log.error("Missing report CSVs (run Spark analytics first): %s", missing)
        return 1
    CH.mkdir(parents=True, exist_ok=True)
    rd = lambda n: pd.read_csv(OUTPUT_DIR / f"{n}.csv")
    _bar(rd("revenue_by_category"), "category", "total_revenue", "Revenue by category", "revenue_by_category.png")
    _bar(rd("revenue_by_region"), "region", "total_revenue", "Revenue by region", "revenue_by_region.png")
    _bar(rd("top_10_stores"), "store_id", "total_revenue", "Top 10 stores by revenue", "top_10_stores.png", True)
    _bar(rd("top_10_products"), "product_id", "total_revenue", "Top 10 products by revenue", "top_10_products.png", True)
    m = rd("monthly_revenue")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for y, g in m.groupby("sales_year"):
        ax.plot(g["sales_month"], g["total_revenue"] / 1e6, marker="o", label=str(y))
    ax.set_xticks(range(1, 13)); ax.set_xlabel("Month"); ax.set_ylabel("Revenue (millions)")
    ax.set_title("Monthly revenue trend"); ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(CH / "monthly_revenue_trend.png", dpi=130); plt.close(fig)
    s = rd("seasonal_revenue").pivot(index="season", columns="sales_year", values="total_revenue")
    s = s.reindex(["Winter", "Spring", "Summer", "Autumn"]) / 1e6
    ax = s.plot(kind="bar", figsize=(8, 4.5), rot=0)
    ax.set_ylabel("Revenue (millions)"); ax.set_title("Seasonal revenue by year")
    ax.figure.tight_layout(); ax.figure.savefig(CH / "seasonal_comparison.png", dpi=130); plt.close(ax.figure)
    log.info("Wrote %d charts to %s", len(list(CH.glob('*.png'))), CH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
