"""Write business insights computed from the actual Spark report CSVs (Member 3)."""
import logging
import sys

import pandas as pd

from src.common import OUTPUT_DIR

log = logging.getLogger("insights")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        rd = lambda n: pd.read_csv(OUTPUT_DIR / f"{n}.csv")
        o, cat, reg = rd("overall_metrics").iloc[0], rd("revenue_by_category"), rd("revenue_by_region")
        st, pr, mo, yr, se = rd("top_10_stores"), rd("top_10_products"), rd("monthly_revenue"), rd("yearly_revenue"), rd("seasonal_revenue")
    except FileNotFoundError as e:
        log.error("Missing input report: %s", e)
        return 1
    tot = o["total_revenue"]
    L = ["# Business insights (computed from the Spark reports)", "",
         f"- Dataset: {int(o['total_transactions']):,} cleaned SYNTHETIC transactions, {int(o['total_units']):,} units, total revenue {tot:,.2f}.",
         f"- Top category: **{cat.iloc[0]['category']}** with {cat.iloc[0]['total_revenue']:,.2f} ({cat.iloc[0]['total_revenue']/tot:.1%} of revenue); weakest: {cat.iloc[-1]['category']} ({cat.iloc[-1]['total_revenue']/tot:.1%}).",
         f"- Top region: **{reg.iloc[0]['region']}** ({reg.iloc[0]['total_revenue']/tot:.1%}); lowest: {reg.iloc[-1]['region']} ({reg.iloc[-1]['total_revenue']/tot:.1%}).",
         f"- Best store: **{st.iloc[0]['store_id']}** ({st.iloc[0]['region']}) with {st.iloc[0]['total_revenue']:,.2f}; best product: **{pr.iloc[0]['product_id']}** ({pr.iloc[0]['category']}) with {pr.iloc[0]['total_revenue']:,.2f}.",
         f"- {int((pr['category']=='Electronics').sum())} of the top 10 products are Electronics.", ]
    best = mo.loc[mo["total_revenue"].idxmax()]
    worst = mo.loc[mo["total_revenue"].idxmin()]
    L.append(f"- Peak month: {int(best['sales_year'])}-{int(best['sales_month']):02d} ({best['total_revenue']:,.2f}); weakest month: {int(worst['sales_year'])}-{int(worst['sales_month']):02d} ({worst['total_revenue']:,.2f}).")
    if len(yr) >= 2:
        a, b = yr.iloc[-2], yr.iloc[-1]
        L.append(f"- Year over year: {int(a['sales_year'])} -> {int(b['sales_year'])} revenue changed by {(b['total_revenue']/a['total_revenue']-1):+.1%}.")
    ls = se[se["sales_year"] == se["sales_year"].max()].sort_values("total_revenue", ascending=False)
    L.append(f"- Strongest season in {int(ls.iloc[0]['sales_year'])}: {ls.iloc[0]['season']} ({ls.iloc[0]['total_revenue']:,.2f}).")
    L += ["", "Note: the data is synthetic and was generated with built-in seasonality, so these insights",
          "demonstrate the analysis method, not real retail behaviour."]
    (OUTPUT_DIR / "business_insights.md").write_text("\n".join(L) + "\n")
    log.info("Wrote business_insights.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
