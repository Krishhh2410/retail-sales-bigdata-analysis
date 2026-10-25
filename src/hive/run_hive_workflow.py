"""Run Hive workflow (cross-platform Python version of run_hive_workflow.sh)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "outputs"
JDBC = "jdbc:hive2://localhost:10000"


def run_beeline(sql_file, extra_args=None):
    cmd = [
        "docker", "compose", "exec", "-T", "hive-server",
        "beeline", "-u", JDBC, "--hivevar", "DATA_ROOT=/retail",
    ]
    if extra_args:
        cmd.extend(extra_args)
    cmd.extend(["-f", sql_file])
    print(f"Running {sql_file}...")
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, stdin=subprocess.DEVNULL)
    if p.returncode != 0:
        print(p.stderr)
        sys.exit(f"ERROR: {sql_file} failed with exit code {p.returncode}")
    return p.stdout


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for f in ["01_create_database", "02_create_tables", "03_create_partitions"]:
        print(f"=== {f}.sql ===")
        out = run_beeline(f"/sql/{f}.sql")
        print(out)

    print("=== 05_validation_queries.sql ===")
    val_out = run_beeline("/sql/05_validation_queries.sql")
    (OUTPUT_DIR / "hive_validation.txt").write_text(val_out, encoding="utf-8")
    print(val_out)

    print("=== 04_analysis_queries.sql (Hive results) ===")
    ana_out = run_beeline("/sql/04_analysis_queries.sql")
    (OUTPUT_DIR / "hive_analysis.txt").write_text(ana_out, encoding="utf-8")
    print(ana_out)

    print("=== export totals for the cross-check ===")
    totals_out = run_beeline("/sql/06_export_totals.sql", extra_args=["--outputformat=csv2", "--silent=true"])
    # Filter out SLF4J or warning lines if any, keeping the CSV header and data
    csv_lines = [l.strip() for l in totals_out.splitlines() if l.strip() and not l.startswith("SLF4J") and not l.startswith("WARNING")]
    clean_csv = "\n".join(csv_lines) + "\n"
    (OUTPUT_DIR / "hive_totals.csv").write_text(clean_csv, encoding="utf-8")
    print(clean_csv)

    if "total_revenue" not in clean_csv:
        sys.exit("ERROR: Hive totals export failed")

    print("Hive workflow finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
