# Data dictionary

**Source:** deterministic SYNTHETIC data from `src/data/generate_data.py` (seed 42, 50,000 base rows + 150 injected duplicates = 50,150 raw rows). These are NOT real business transactions. No external dataset/licence is involved. Date range 2024-01-01 .. 2025-12-31, 5 regions, 20 stores (4 per region), 6 categories, 42 products.

| Column | Type (Hive) | Rule |
|---|---|---|
| transaction_id | STRING | unique, `T` + 8 digits |
| sale_date | DATE (STRING in staging) | ISO `YYYY-MM-DD`, within the date range |
| region | STRING (partition column in `sales_partitioned`) | North, South, East, West, Central |
| store_id | STRING | S01..S20 |
| product_id | STRING | P001..P042 |
| category | STRING | Electronics, Grocery, Clothing, Home & Kitchen, Beauty, Sports |
| quantity | INT | integer 1..1000 |
| unit_price | DECIMAL(12,2) | > 0 |
| sales_amount | DECIMAL(14,2) | `quantity * unit_price`, recomputed during cleaning |
| sales_year, sales_month | INT (partition columns) | derived from `sale_date`; month not zero-padded |

## Cleaning rules (first failing rule wins)
missing value -> unexpected region -> unexpected category -> invalid/out-of-range date -> invalid quantity -> invalid price -> duplicate `transaction_id` (first kept).
Not rejected but fixed: whitespace/case of region and category, `YYYY/MM/DD` and `DD-MM-YYYY` dates, wrong `sales_amount` (recomputed).

## Files
* `data/retail_sales_raw.csv` - raw, with deliberately injected defects.
* `data/retail_sales.csv` - cleaned, 9 columns, header, region included (loaded into `staging_sales`).
* `outputs/warehouse/region=X/sales_year=Y/sales_month=M/part-00000.csv` - 8 columns, **no header, no region** (loaded into `sales_partitioned`).
* `data/rejected_rows.csv`, `data/cleaning_report.json`.

Regenerate: `python -m src.data.generate_data --rows 50000 --seed 42`.
