"""Upload cleaned data to HDFS (cross-platform Python version of upload_data.sh)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = ROOT / "data" / "retail_sales.csv"
WAREHOUSE_DIR = ROOT / "outputs" / "warehouse"


def run(cmd, check=True):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=ROOT, check=check, text=True, capture_output=True)


def main():
    if not DATA_CSV.exists():
        sys.exit("ERROR: data/retail_sales.csv missing - run the cleaning step")
    if not WAREHOUSE_DIR.exists():
        sys.exit("ERROR: outputs/warehouse missing - run prepare_partitions")

    print("[1/5] create HDFS directories")
    run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfs", "-mkdir", "-p", "/retail/staging", "/retail/warehouse"])

    print("[2/5] copy files into the NameNode container")
    p = run(["docker", "compose", "ps", "-q", "namenode"])
    cid = p.stdout.strip()
    if not cid:
        sys.exit("ERROR: NameNode container not found")

    run(["docker", "exec", cid, "rm", "-rf", "/tmp/upload"])
    run(["docker", "exec", cid, "mkdir", "-p", "/tmp/upload"])
    run(["docker", "cp", str(DATA_CSV), f"{cid}:/tmp/upload/retail_sales.csv"])
    run(["docker", "cp", str(WAREHOUSE_DIR), f"{cid}:/tmp/upload/sales"])

    print("[3/5] staging file -> /retail/staging")
    run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfs", "-put", "-f", "/tmp/upload/retail_sales.csv", "/retail/staging/retail_sales.csv"])

    print("[4/5] partition tree -> /retail/warehouse/sales (old tree removed first)")
    run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfs", "-rm", "-r", "-f", "/retail/warehouse/sales"], check=False)
    run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfs", "-put", "/tmp/upload/sales", "/retail/warehouse/sales"])

    print("[5/5] listing")
    p1 = run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfs", "-ls", "/retail/staging"])
    print(p1.stdout)
    p2 = run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfs", "-ls", "/retail/warehouse/sales"])
    print(p2.stdout)

    print("Upload finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
