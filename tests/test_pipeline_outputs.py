"""Needs the pipeline to have produced outputs/ (skipped otherwise). Not proof of cluster execution."""
import pytest

from src.common import OUTPUT_DIR
from src.pipeline.validate_outputs import run_checks

pytestmark = pytest.mark.outputs


def test_final_validation_checks_pass():
    if not (OUTPUT_DIR / "overall_metrics.csv").exists():
        pytest.skip("run the pipeline first: python -m src.pipeline.run_pipeline --mode local")
    failed = [r for r in run_checks(require_hive=False) if not r[1]]
    assert not failed, failed
