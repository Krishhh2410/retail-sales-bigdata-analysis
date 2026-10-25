"""Verify HDFS storage and replication (cross-platform Python version of verify_hdfs.sh)."""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_CSV = ROOT / "data" / "retail_sales.csv"
OUTPUT_DIR = ROOT / "outputs"


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_lines = []

    out_lines.append("### DataNode report (expect 'Live datanodes (3)')")
    p = run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfsadmin", "-report"])
    filtered = [l for l in p.stdout.splitlines() if any(k in l for k in ["Live datanodes", "Name:", "DFS Used:", "Hostname"])]
    out_lines.extend(filtered)

    out_lines.append("\n### Safe mode")
    p = run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfsadmin", "-safemode", "get"])
    out_lines.append(p.stdout.strip())

    out_lines.append("\n### Directory tree")
    p = run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfs", "-ls", "-R", "/retail"])
    tree = p.stdout.splitlines()[:40]
    out_lines.extend(tree)

    out_lines.append("\n### Space used")
    p = run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfs", "-du", "-h", "/retail"])
    out_lines.append(p.stdout.strip())

    out_lines.append("\n### fsck: blocks, replication, DataNode locations for the staging file")
    p = run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "fsck", "/retail/staging/retail_sales.csv", "-files", "-blocks", "-locations"])
    out_lines.append(p.stdout.strip())

    out_lines.append("\n### First 3 lines of staged file read back from HDFS")
    p = run(["docker", "compose", "exec", "-T", "namenode", "hdfs", "dfs", "-cat", "/retail/staging/retail_sales.csv"])
    cat_head = p.stdout.splitlines()[:3]
    out_lines.extend(cat_head)

    verification_text = "\n".join(out_lines) + "\n"
    verification_path = OUTPUT_DIR / "hdfs_verification.txt"
    verification_path.write_text(verification_text, encoding="utf-8")
    print(verification_text)

    print("\n### Round-trip checksum (local file vs file read back from HDFS)")
    local_md5 = hashlib.md5(DATA_CSV.read_bytes()).hexdigest()
    remote_p = run(["docker", "compose", "exec", "-T", "namenode", "md5sum", "/tmp/upload/retail_sales.csv"])
    remote_md5 = remote_p.stdout.strip().split()[0] if remote_p.stdout.strip() else ""

    print(f"local={local_md5} hdfs={remote_md5}")
    if local_md5 != remote_md5:
        sys.exit("CHECKSUM MISMATCH")
    print("CHECKSUM MATCH")

    if "Live datanodes (3)" not in verification_text:
        sys.exit("ERROR: expected 3 live DataNodes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
