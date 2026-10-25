import pytest


@pytest.fixture(scope="session")
def spark():
    pyspark = pytest.importorskip("pyspark")
    from src.analytics.spark_session import build_session
    s = build_session("pytest", hive=False, master="local[2]")
    yield s
    s.stop()
