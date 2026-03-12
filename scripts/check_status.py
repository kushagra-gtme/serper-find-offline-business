#!/usr/bin/env python3
"""
Check the status of a search run.

Usage:
    python scripts/check_status.py --run-id <id>
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.storage import FileManager
from lib.utils import sanitize_run_id


def check_status(run_id: str, data_dir: Path) -> dict:
    fm = FileManager(data_dir)
    run_path = fm.get_run_path(run_id)

    if not run_path.exists():
        return {"status": "error", "message": f"Run {run_id} not found"}

    result = {"run_id": run_id}

    # Load run config
    run_json = run_path / "run.json"
    if run_json.exists():
        result["config"] = fm.read_json(run_json)

    # Load progress
    progress_json = run_path / "progress.json"
    if progress_json.exists():
        result["progress"] = fm.read_json(progress_json)
        result["status"] = result["progress"].get("status", "unknown")
    else:
        result["status"] = "unknown"

    # Results count
    results_csv = run_path / "results.csv"
    if results_csv.exists():
        result["results_count"] = fm.count_csv_rows(results_csv)

    # Webhook status
    webhook_json = run_path / "webhook.json"
    if webhook_json.exists():
        result["webhook"] = fm.read_json(webhook_json)

    # Summary
    summary_json = run_path / "summary.json"
    if summary_json.exists():
        result["summary"] = fm.read_json(summary_json)

    # Error details
    error_json = run_path / "error.json"
    if error_json.exists():
        result["error_details"] = fm.read_json(error_json)

    return result


def main():
    parser = argparse.ArgumentParser(description="Check status of a search run")
    parser.add_argument("--run-id", required=True, help="Run ID to check")
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory")
    args = parser.parse_args()

    err = sanitize_run_id(args.run_id)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    data_dir = Path(args.data_dir) if args.data_dir else Path(__file__).parent.parent / "data"
    result = check_status(args.run_id, data_dir)
    print(json.dumps(result, indent=2))

    if result.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
