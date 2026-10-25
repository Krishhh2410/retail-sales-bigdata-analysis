import pandas as pd
import pytest

from src.common import COLUMNS, partition_path
from src.data.clean_data import clean_dataframe
from src.data.generate_data import generate_clean_rows, inject_issues
from src.data.prepare_partitions import build_partitions
import random


def raw(rows):
    return pd.DataFrame(rows, columns=COLUMNS, dtype=str)


def row(**kw):
    base = dict(transaction_id="T1", sale_date="2025-03-05", region="West", store_id="S13", product_id="P001",
                category="Grocery", quantity="2", unit_price="3.50", sales_amount="7.00")
    base.update(kw)
    return base


def reasons(rows):
    _, rej, rep = clean_dataframe(raw(rows))
    return rep["rejected_by_reason"]


def test_generator_is_deterministic():
    assert generate_clean_rows(200, 7) == generate_clean_rows(200, 7)
    assert generate_clean_rows(200, 7) != generate_clean_rows(200, 8)


def test_generated_schema_and_sales_amount():
    rows = generate_clean_rows(500, 1)
    assert list(rows[0].keys()) == COLUMNS
    assert all(abs(int(r["quantity"]) * float(r["unit_price"]) - float(r["sales_amount"])) < 0.005 for r in rows)


def test_valid_row_passes_unchanged():
    clean, rej, rep = clean_dataframe(raw([row()]))
    assert len(clean) == 1 and rej.empty and rep["rejected_rows"] == 0


@pytest.mark.parametrize("kw,reason", [
    (dict(quantity="-1"), "invalid_quantity"), (dict(quantity="0"), "invalid_quantity"),
    (dict(quantity="2.5"), "invalid_quantity"), (dict(quantity="abc"), "invalid_quantity"),
    (dict(unit_price="0"), "invalid_price"), (dict(unit_price="-3"), "invalid_price"),
    (dict(unit_price="x"), "invalid_price"),
    (dict(sale_date="2025-02-30"), "invalid_date"), (dict(sale_date="garbage"), "invalid_date"),
    (dict(sale_date="2019-01-01"), "invalid_date"),
    (dict(category="Misc"), "unexpected_category"), (dict(region="Mars"), "unexpected_region"),
    (dict(store_id=""), "missing_value"), (dict(product_id="NULL"), "missing_value"),
])
def test_invalid_rows_are_rejected_with_reason(kw, reason):
    assert reasons([row(**kw)]) == {reason: 1}


def test_duplicate_transaction_ids_keep_first_only():
    clean, rej, rep = clean_dataframe(raw([row(), row(), row(transaction_id="T2")]))
    assert len(clean) == 2 and rep["rejected_by_reason"] == {"duplicate_transaction_id": 1}


def test_text_and_dates_are_standardised():
    clean, _, rep = clean_dataframe(raw([row(region="  west ", sale_date="2025/03/05", category="grocery")]))
    r = clean.iloc[0]
    assert (r["region"], r["sale_date"], r["category"]) == ("West", "2025-03-05", "Grocery")
    assert rep["dates_reformatted_to_iso"] == 1


def test_wrong_sales_amount_is_recomputed():
    clean, _, rep = clean_dataframe(raw([row(sales_amount="99.99")]))
    assert clean.iloc[0]["sales_amount"] == 7.00 and rep["sales_amount_recomputed"] == 1


def test_missing_columns_raise():
    with pytest.raises(ValueError):
        clean_dataframe(pd.DataFrame({"a": ["1"]}))


def test_injected_issues_are_all_caught():
    rng = random.Random(3)
    rows = generate_clean_rows(3000, 3)
    inject_issues(rows, rng)
    clean, rej, rep = clean_dataframe(raw(rows))
    assert clean["transaction_id"].is_unique and not clean.isna().any().any()
    # 150 copies were injected; a copy is only "rejected as duplicate" if its original survived
    # cleaning (otherwise the valid copy is correctly kept instead).
    assert 0 < rep["rejected_by_reason"]["duplicate_transaction_id"] <= 150
    assert rep["clean_rows"] + rep["rejected_rows"] == len(rows)


def test_partition_path_format():
    assert partition_path("West", 2025, 1) == "region=West/sales_year=2025/sales_month=1"


def test_partition_tree_has_no_region_column_and_all_rows(tmp_path):
    clean, _, _ = clean_dataframe(raw(generate_clean_rows(400, 5)))
    src = tmp_path / "clean.csv"
    clean.to_csv(src, index=False, float_format="%.2f")
    n = build_partitions(src, tmp_path / "wh")
    files = list((tmp_path / "wh").rglob("part-00000.csv"))
    assert n == len(files) > 0
    total = 0
    for f in files:
        first = f.read_text().splitlines()[0].split(",")
        assert len(first) == 8 and first[0].startswith("T")  # no header, no region column
        total += sum(1 for _ in open(f))
    assert total == len(clean)
