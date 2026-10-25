import pandas as pd
import pytest

from src.analytics import local_analysis as la
from src.analytics.spark_analysis import QUERIES
from src.data.clean_data import clean_dataframe
from src.data.generate_data import generate_clean_rows
from src.common import COLUMNS

TINY = pd.DataFrame([
    ("T1", "2025-01-10", "West", "S13", "P001", "Grocery", 2, 5.0, 10.0),
    ("T2", "2025-01-20", "West", "S13", "P002", "Sports", 1, 20.0, 20.0),
    ("T3", "2025-02-02", "East", "S05", "P001", "Grocery", 3, 5.0, 15.0),
    ("T4", "2024-07-01", "East", "S05", "P003", "Beauty", 1, 40.0, 40.0),
], columns=COLUMNS)


def test_overall_and_category():
    o = la.overall(TINY).iloc[0]
    assert (o.total_transactions, o.total_units, o.total_revenue) == (4, 7, 85.0)
    c = la.by_category(TINY).set_index("category")
    assert c.loc["Grocery", "total_revenue"] == 25.0 and c.loc["Beauty", "total_units"] == 1


def test_monthly_and_seasonal():
    m = la.monthly(TINY)
    assert list(zip(m.sales_year, m.sales_month, m.total_revenue)) == [(2024, 7, 40.0), (2025, 1, 30.0), (2025, 2, 15.0)]
    s = la.seasonal(TINY).set_index(["sales_year", "season"])
    assert s.loc[(2025, "Winter"), "total_revenue"] == 45.0 and s.loc[(2024, "Summer"), "total_revenue"] == 40.0


def test_top_n_ordering_is_deterministic():
    assert la.top_stores(TINY, 1).iloc[0]["store_id"] == "S05"  # 55 vs 30


@pytest.mark.spark
def test_spark_matches_pandas_reference(spark):
    """Local Spark session (no Hive, no cluster) vs the pandas oracle on the same data."""
    clean, _, _ = clean_dataframe(pd.DataFrame(generate_clean_rows(3000, 11), dtype=str))
    sdf = spark.createDataFrame(clean)
    sdf = sdf.selectExpr("*", "CAST(substring(sale_date,1,4) AS INT) AS sales_year",
                         "CAST(substring(sale_date,6,2) AS INT) AS sales_month")
    sdf.createOrReplaceTempView("sales")
    for name, ref in [("revenue_by_category", la.by_category(clean)), ("revenue_by_region", la.by_region(clean)),
                      ("monthly_revenue", la.monthly(clean)), ("top_10_stores", la.top_stores(clean)),
                      ("top_10_products", la.top_products(clean)), ("seasonal_revenue", la.seasonal(clean))]:
        got = spark.sql(QUERIES[name].format(t="sales")).toPandas()
        assert len(got) == len(ref), name
        assert (got["total_units"].values == ref["total_units"].values).all(), name
        assert pytest.approx(got["total_revenue"].values, abs=0.01) == ref["total_revenue"].values, name
