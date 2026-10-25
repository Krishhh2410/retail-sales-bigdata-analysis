# Test plan
## Runs locally (no cluster): `python -m pytest -q`
| Test file | Covers |
|---|---|
| `tests/test_data_quality.py` | schema, determinism, every rejection rule, duplicates, standardisation, recomputed amounts, partition path format, partition tree shape (no header/no region), injected defects all caught |
| `tests/test_aggregations.py` | hand-computed totals, category/monthly/seasonal/top-N logic, and **Spark (local session) = pandas oracle** on the same data for 6 reports |
| `tests/test_pipeline_outputs.py` | runs the final validator on `outputs/` (skipped if the pipeline was not run) |

## Needs the pipeline run (still local)
`python -m src.pipeline.validate_outputs` - 31 checks: row counts raw = clean + rejected, no duplicate ids/nulls, amount = qty x price, partition rows = clean rows, Spark = cleaned totals, report sums = total revenue, outputs exist. Money tolerance: 0.01 absolute.

## Needs the live cluster (NOT covered by pytest)
`verify_hdfs.sh` (3 live DataNodes, fsck replication, checksum), `run_hive_workflow.sh` (beeline DDL/MSCK/queries), `spark_analysis --mode hive` in `spark-client`, `validate_outputs --require-hive` (Hive = Spark totals).

**A passing local unit test is not evidence that HDFS/Hive/Spark integration works.**
