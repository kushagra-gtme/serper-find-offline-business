#!/usr/bin/env python3
"""
List all previous search runs.

Usage:
    python scripts/list_runs.py
    python scripts/list_runs.py --data-dir ./data
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.storage import FileManager


def list_runs(data_dir: Path) -> dict:
    fm = FileManager(data_dir)
    runs = fm.list_runs()

    summary = []
    for run in runs:
        entry = {
            "run_id": run.get("run_id", "unknown"),
            "created_at": run.get("created_at", "unknown"),
            "states": run.get("states", []),
            "search_terms": run.get("search_terms", []),
            "total_queries": run.get("total_queries", 0),
        }
        if "progress" in run:
            p = run["progress"]
            entry["status"] = p.get("status", "unknown")
            entry["completed_batches"] = p.get("completed_batches", 0)
            entry["total_batches"] = p.get("total_batches", 0)

        # Count results
        run_path = fm.get_run_path(entry["run_id"])
        results_csv = run_path / "results.csv"
        if results_csv.exists():
            entry["results_count"] = fm.count_csv_rows(results_csv)

        summary.append(entry)

    return {"total_runs": len(summary), "runs": summary}


def main():
    parser = argparse.ArgumentParser(description="List all search runs")
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else Path(__file__).parent.parent / "data"
    result = list_runs(data_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
