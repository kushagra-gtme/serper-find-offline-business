#!/usr/bin/env python3
"""
Resume a failed search from a specific batch.

Usage:
    python scripts/resume_search.py --run-id <id> --start-batch 5
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from lib.client import SerperClient, SerperAPIError
from lib.models import Query, Place, RunConfig, RunProgress, PlaceFilters
from lib.storage import FileManager
from lib.filters import filter_places, deduplicate_places, normalize_url
from lib.utils import setup_logging, batch_list, sanitize_run_id


def extract_places(result: list) -> list:
    """Extract Place objects from Serper API batch response."""
    places = []
    if not isinstance(result, list):
        return places
    for qr in result:
        params = qr.get("searchParameters", {})
        for p in qr.get("places", []):
            raw_website = p.get("website")
            places.append(Place(
                q=params.get("q", ""),
                location=params.get("location", ""),
                page=params.get("page", 1),
                position=p.get("position", 0),
                title=p.get("title", ""),
                address=p.get("address", ""),
                latitude=p.get("latitude"),
                longitude=p.get("longitude"),
                rating=p.get("rating"),
                ratingCount=p.get("ratingCount"),
                category=p.get("category"),
                phoneNumber=p.get("phoneNumber"),
                website=raw_website,
                website_normalized=normalize_url(raw_website),
                cid=p.get("cid"),
            ))
    return places


async def resume_search(run_id: str, start_batch: int, data_dir: Path, api_key: str) -> dict:
    logger = logging.getLogger("serper")
    fm = FileManager(data_dir)
    run_path = fm.get_run_path(run_id)

    if not run_path.exists():
        return {"status": "error", "message": f"Run {run_id} not found"}

    # Load config, progress, filters
    config = RunConfig.from_dict(fm.read_json(run_path / "run.json"))
    progress = RunProgress.from_dict(fm.read_json(run_path / "progress.json"))

    filters_path = run_path / "filters.json"
    filters = PlaceFilters.from_dict(fm.read_json(filters_path)) if filters_path.exists() else PlaceFilters()

    # Load queries
    headers, rows = fm.read_csv(run_path / "queries.csv")
    queries = [Query(q=row[0], location=row[1], page=int(row[2])) for row in rows]

    batch_size = 100
    batches = list(batch_list(queries, batch_size))

    if start_batch >= len(batches):
        return {"status": "error", "message": f"start_batch ({start_batch}) >= total batches ({len(batches)})"}

    # Count existing places
    results_file = run_path / "results.csv"
    total_places = fm.count_csv_rows(results_file) if results_file.exists() else 0

    completed = progress.completed_batches
    failed = progress.failed_queries

    print(f"Resuming {run_id} from batch {start_batch} (previously: {completed} batches, {total_places} places)", file=sys.stderr)

    # File logging
    log_handler = logging.FileHandler(run_path / "execution.log", mode="a")
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(log_handler)

    progress.status = "executing"
    await fm.write_json(run_path / "progress.json", progress.to_dict())

    async with SerperClient(api_key) as client:
        for idx in range(start_batch, len(batches)):
            batch = batches[idx]
            progress.current_batch = idx
            logger.info(f"[RESUME] Batch {idx + 1}/{len(batches)}")

            try:
                result = await client.batch_search_places(batch)
                await fm.append_jsonl(run_path / "raw" / f"batch-{idx + 1:03d}.jsonl", result)
                completed += 1

                batch_places = extract_places(result)

                if batch_places:
                    batch_places, _ = filter_places(batch_places, filters)
                if batch_places:
                    batch_places, _ = deduplicate_places(batch_places, filters.dedupe_by)
                if batch_places:
                    await fm.append_csv_rows(
                        results_file, Place.csv_headers(), [p.to_csv_row() for p in batch_places]
                    )
                    total_places += len(batch_places)

            except SerperAPIError as e:
                logger.error(f"[RESUME] Batch {idx + 1} failed: {e}")
                failed += len(batch)
                await fm.write_json(run_path / "error.json", {
                    "batch": idx,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "resume_command": f"python scripts/resume_search.py --run-id {run_id} --start-batch {idx}",
                })
                progress.status = "error"
                progress.completed_batches = completed
                progress.failed_queries = failed
                progress.last_updated = datetime.now()
                await fm.write_json(run_path / "progress.json", progress.to_dict())
                logger.removeHandler(log_handler)
                log_handler.close()
                return {"status": "error", "run_id": run_id, "failed_batch": idx, "total_places": total_places}

            progress.completed_batches = completed
            progress.failed_queries = failed
            progress.last_updated = datetime.now()
            await fm.write_json(run_path / "progress.json", progress.to_dict())

            if idx < len(batches) - 1:
                await asyncio.sleep(0.5)

            if (idx + 1 - start_batch) % 5 == 0 or idx == len(batches) - 1:
                print(f"  [{idx + 1}/{len(batches)}] {total_places:,} places", file=sys.stderr)

    progress.status = "completed" if failed == 0 else "completed_with_errors"
    progress.last_updated = datetime.now()
    await fm.write_json(run_path / "progress.json", progress.to_dict())

    logger.removeHandler(log_handler)
    log_handler.close()

    summary = {
        "status": progress.status,
        "run_id": run_id,
        "total_places": total_places,
        "completed_batches": completed,
        "total_batches": len(batches),
        "failed_queries": failed,
    }
    await fm.write_json(run_path / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Resume a failed search from a specific batch")
    parser.add_argument("--run-id", required=True, help="Run ID to resume")
    parser.add_argument("--start-batch", type=int, required=True, help="Batch to resume from (0-indexed)")
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory")
    args = parser.parse_args()

    setup_logging()

    err = sanitize_run_id(args.run_id)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("Error: SERPER_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    data_dir = Path(args.data_dir) if args.data_dir else Path(__file__).parent.parent / "data"
    result = asyncio.run(resume_search(args.run_id, args.start_batch, data_dir, api_key))

    if result.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
