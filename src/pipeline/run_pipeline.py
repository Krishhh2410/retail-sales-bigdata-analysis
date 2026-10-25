"""End-to-end orchestrator. Stops at the first failed stage.

  python -m src.pipeline.run_pipeline --mode local     # Spark + embedded Hive metastore, local files
  python -m src.pipeline.run_pipeline --mode cluster   # Docker: HDFS + Hive + Spark client

Stage timings are written to outputs/pipeline_timings.json (real measurements of this run).
"""
import argparse
import json
import logging
import subprocess
import sys
import time

from src.common import OUTPUT_DIR, RAW_CSV, ROOT

log = logging.getLogger("pipeline")
PY = sys.executable


def sh(*cmd, timeout=None):
    log.info("$ %s", " ".join(cmd))
    return subprocess.run(list(cmd), cwd=ROOT, timeout=timeout).returncode


def wait_for(desc, check, timeout, interval=5):
    end = time.time() + timeout
    while time.time() < end:
        if check():
            return 0
        time.sleep(interval)
    log.error("Timed out waiting for %s", desc)
    return 1


def hdfs_ready():
    p = subprocess.run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfsadmin", "-report"],
                       cwd=ROOT, capture_output=True, text=True)
    return "Live datanodes (3)" in p.stdout


def hive_ready():
    return subprocess.run(["docker", "compose", "exec", "-T", "hive-server", "beeline", "-u",
                           "jdbc:hive2://localhost:10000", "-e", "SHOW DATABASES;"],
                          cwd=ROOT, capture_output=True).returncode == 0


def stages(mode, skip_generate):
    s = []
    if not (skip_generate and RAW_CSV.exists()):
        s.append(("generate data", lambda: sh(PY, "-m", "src.data.generate_data")))
    s += [("clean + validate data", lambda: sh(PY, "-m", "src.data.clean_data")),
          ("prepare partition tree", lambda: sh(PY, "-m", "src.data.prepare_partitions"))]
    if mode == "local":
        s.append(("Spark analytics (local Hive metastore)", lambda: sh(PY, "-m", "src.analytics.spark_analysis", "--mode", "local-hive")))
    else:
        upload_cmd = [PY, "-m", "src.hdfs.upload_data"] if sys.platform == "win32" else ["bash", "src/hdfs/upload_data.sh"]
        verify_cmd = [PY, "-m", "src.hdfs.verify_hdfs"] if sys.platform == "win32" else ["bash", "src/hdfs/verify_hdfs.sh"]
        hive_cmd = [PY, "-m", "src.hive.run_hive_workflow"] if sys.platform == "win32" else ["bash", "src/hive/run_hive_workflow.sh"]
        s += [("start docker cluster", lambda: sh("docker", "compose", "up", "-d")),
              ("wait for NameNode + 3 DataNodes", lambda: wait_for("3 live DataNodes", hdfs_ready, 240)),
              ("upload to HDFS", lambda: sh(*upload_cmd)),
              ("verify HDFS", lambda: sh(*verify_cmd)),
              ("wait for HiveServer2", lambda: wait_for("HiveServer2", hive_ready, 420, 10)),
              ("Hive DDL, partitions, validation", lambda: sh(*hive_cmd)),
              ("Spark analytics (Hive on HDFS)", lambda: sh("docker", "compose", "run", "--rm", "spark-client",
                                                          "python", "-m", "src.analytics.spark_analysis", "--mode", "hive"))]
    s += [("charts", lambda: sh(PY, "-m", "src.analytics.make_charts")),
          ("business insights", lambda: sh(PY, "-m", "src.analytics.generate_insights")),
          ("final validation", lambda: sh(PY, "-m", "src.pipeline.validate_outputs", *(["--require-hive"] if mode == "cluster" else [])))]
    return s


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=["local", "cluster"], default="local")
    ap.add_argument("--skip-generate", action="store_true", help="reuse existing data/retail_sales_raw.csv")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    timings = {}
    for name, fn in stages(args.mode, args.skip_generate):
        log.info("=== STAGE: %s ===", name)
        t = time.time()
        rc = fn()
        timings[name] = round(time.time() - t, 1)
        if rc != 0:
            log.error("STAGE FAILED: %s (exit %s). Pipeline stopped; later stages were NOT run.", name, rc)
            return rc or 1
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "pipeline_timings.json").write_text(json.dumps({"mode": args.mode, "seconds": timings}, indent=2))
    log.info("PIPELINE OK (%s mode). Timings: %s", args.mode, timings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
