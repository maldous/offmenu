"""Offline-only bounded DuckDB connection factory and synthetic verification.

Invoke with python3 -I -S <installed>/runtime.py --smoke. For application code,
explicitly import this module and pass authorized local read/write directories.
The containing process/jail is the security boundary, not DuckDB settings alone.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import tempfile
import time

VERSION = "1.5.6"
ROOT = Path(__file__).resolve().parent


def validated_budget(overrides=None):
    """Reviewed explicit overrides may reduce, never exceed, baseline budgets."""
    budget = {"threads": 4, "memory_gib": 8, "temp_gib": 20}
    for name, value in (overrides or {}).items():
        if name not in budget or type(value) is not int or not 1 <= value <= budget[name]:
            raise ValueError("Budget must be an integer within the approved baseline ceiling")
        budget[name] = value
    return budget


def connect(allowed_directories, temp_directory, *, budget=None):
    """Use only caller-authorized directories; never automatic remote access."""
    if not allowed_directories:
        raise ValueError("Explicit authorized local directories are required")
    dirs = []
    for value in allowed_directories:
        path = Path(value)
        if not path.is_absolute() or not path.is_dir() or path.is_symlink():
            raise ValueError("Expected existing absolute non-symlink directory")
        if path.resolve() != path:
            raise ValueError("Directory ancestors must not be symlinks")
        dirs.append(str(path) + os.sep)
    temp = Path(temp_directory)
    if not temp.is_absolute() or not temp.is_dir() or temp.resolve() != temp:
        raise ValueError("Expected existing absolute non-symlink temp directory")
    if not any(temp.is_relative_to(Path(d)) for d in dirs):
        raise ValueError("Temp directory must lie inside an authorized directory")
    limits = validated_budget(budget)
    sys.path.insert(0, str(ROOT / "venv" / "lib" / "python3.12" / "site-packages"))
    import duckdb
    if duckdb.__version__ != VERSION:
        raise RuntimeError("Unexpected DuckDB version")
    con = duckdb.connect(":memory:", config={
        "threads": str(limits["threads"]),
        "memory_limit": str(limits["memory_gib"]) + "GiB",
        "max_temp_directory_size": str(limits["temp_gib"]) + "GiB",
        "temp_directory": str(temp),
        "autoinstall_known_extensions": "false",
        "autoload_known_extensions": "false",
        "allow_community_extensions": "false",
        "allow_unsigned_extensions": "false",
    })
    # DuckDB's config-map application order is not Python insertion order.
    # Set the allowlist while configuration is open, then disable all other
    # external access and lock, before returning or executing any workload.
    try:
        # Verified on pinned DuckDB: allowed_directories is post-start only;
        # bind the list as data, before disabling external access and locking.
        con.execute("SET allowed_directories = ?", [dirs])
        con.execute("SET enable_external_access = false")
        con.execute("SET lock_configuration = true")
    except BaseException:
        con.close()
        raise
    return con


def smoke():
    """Ten thousand generated rows; never opens corpus or raw data files."""
    started = time.monotonic()
    scratch = ROOT / "scratch"
    scratch.mkdir(mode=0o700, exist_ok=True)
    if scratch.is_symlink() or scratch.resolve() != scratch:
        raise ValueError("Unsafe scratch directory")
    with tempfile.TemporaryDirectory(prefix="synthetic-", dir=scratch) as td:
        directory = Path(td)
        temp = directory / "spill"
        temp.mkdir(mode=0o700)
        con = connect([directory], temp)
        timings = {"startup_seconds": round(time.monotonic() - started, 6)}
        try:
            step = time.monotonic()
            con.execute("CREATE TABLE synthetic AS SELECT i::BIGINT AS id, "
                        "('category-' || (i % 8)::VARCHAR) AS category, "
                        "(i % 97)::DOUBLE / 10 AS amount FROM range(10000) t(i)")
            timings["generate_seconds"] = round(time.monotonic() - step, 6)
            parquet = directory / "synthetic.parquet"
            # Parameter binding is supported for COPY target paths.
            step = time.monotonic()
            con.execute("COPY synthetic TO ? (FORMAT PARQUET, COMPRESSION ZSTD)", [str(parquet)])
            timings["parquet_write_seconds"] = round(time.monotonic() - step, 6)
            step = time.monotonic()
            got = con.execute("SELECT count(*), sum(id), count(DISTINCT category) FROM read_parquet(?)", [str(parquet)]).fetchone()
            timings["parquet_readback_seconds"] = round(time.monotonic() - step, 6)
            if got != (10000, 49995000, 8):
                raise RuntimeError("Parquet roundtrip mismatch")
            step = time.monotonic()
            groups = con.execute("SELECT category, count(*), round(sum(amount),3) FROM read_parquet(?) "
                                 "GROUP BY category ORDER BY category", [str(parquet)]).fetchall()
            timings["parquet_groupby_seconds"] = round(time.monotonic() - step, 6)
            if len(groups) != 8 or any(row[1] != 1250 for row in groups):
                raise RuntimeError("Synthetic grouping mismatch")
            settings = dict(con.execute("SELECT name, value FROM duckdb_settings() WHERE name IN "
                                       "('threads','memory_limit','max_temp_directory_size',"
                                       "'autoinstall_known_extensions','autoload_known_extensions',"
                                       "'enable_external_access','lock_configuration')").fetchall())
            return {
                "ok": True, "dataset": "synthetic-only", "duckdb_version": VERSION,
                "rows": got[0], "sum_id": got[1], "distinct_categories": got[2],
                "parquet_bytes": parquet.stat().st_size,
                "parquet_sha256": hashlib.sha256(parquet.read_bytes()).hexdigest(),
                "grouped_result_sha256": hashlib.sha256(json.dumps(groups, separators=(",", ":")).encode()).hexdigest(),
                "group_count": len(groups), "timings": timings,
                "elapsed_seconds": round(time.monotonic() - started, 6),
                "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                "settings": settings,
                "note": "Single synthetic verification trial, not a throughput/speedup/optimum claim. Buffer/spill/thread settings are not OS-level total process limits.",
            }
        finally:
            con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(smoke(), sort_keys=True))
