#!/usr/bin/env python3
"""
Search for offline businesses using Serper Places API.

Usage:
    python scripts/search.py --terms "dentist" --states CA TX --pages 3
    python scripts/search.py --terms "plumber" "electrician" --states NY --dry-run
    python scripts/search.py --terms "dentist" --states CA --cities 5 --min-rating 4.0
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

# Add parent dir so "lib" is importable
sys.path.insert(0, str(Path(__file__).parent))

from lib.client import SerperClient, SerperAPIError
from lib.models import Query, Place, RunConfig, RunProgress, PlaceFilters
from lib.storage import FileManager
from lib.filters import filter_places, deduplicate_places
from lib.extract import extract_places, BATCH_SIZE
from lib.locations import load_cities, filter_cities_by_states, get_state_locations
from lib.utils import (
    setup_logging,
    batch_list,
    progress_msg,
    validate_search_inputs,
)


async def run_search(args, data_dir: Path, api_key: str) -> dict:
    logger = logging.getLogger("serper")

    # Load locations
    if args.use_state_level:
        locations = get_state_locations(args.states)
        location_type = "states"
    else:
        cities_path = data_dir / "cities.csv"
        all_cities = load_cities(cities_path)
        locations = filter_cities_by_states(all_cities, args.states, limit_per_state=args.cities)
        location_type = "cities"

    if not locations:
        return {"status": "error", "message": f"No locations found for states: {args.states}"}

    # Generate queries
    queries = []
    for term in args.terms:
        for loc in locations:
            for page in range(1, args.pages + 1):
                queries.append(Query(q=term, location=loc, page=page))

    total_batches = (len(queries) + BATCH_SIZE - 1) // BATCH_SIZE
    cost_estimate = len(queries)

    # Dry run
    if args.dry_run:
        summary = {
            "status": "dry_run",
            "total_queries": len(queries),
            "total_batches": total_batches,
            "locations_count": len(locations),
            "location_type": location_type,
            "states": args.states,
            "search_terms": args.terms,
            "pages_per_query": args.pages,
            "estimated_api_credits": cost_estimate,
        }
        print(json.dumps(summary, indent=2))
        return summary

    # Create run folder
    fm = FileManager(data_dir)
    run_id, run_path = fm.create_run_folder(args.terms, args.states, locations if location_type == "cities" else None)

    # Build filters
    filters = PlaceFilters(
        min_rating=args.min_rating,
        min_review_count=args.min_reviews,
        require_website=args.require_website,
        require_phone=args.require_phone,
        require_address=args.require_address,
        exclude_keywords=args.exclude_keywords,
        dedupe_by=args.dedupe_by,
    )

    # Save run config
    config = RunConfig(
        run_id=run_id,
        created_at=datetime.now(),
        states=args.states,
        search_terms=args.terms,
        pages_per_query=args.pages,
        total_queries=len(queries),
        cities=locations if location_type == "cities" else None,
    )
    await fm.write_json(run_path / "run.json", config.to_dict())
    await fm.write_json(run_path / "filters.json", filters.to_dict())

    # Save queries CSV
    q_headers = ["q", "location", "page"]
    q_rows = [[q.q, q.location, str(q.page)] for q in queries]
    await fm.write_csv(run_path / "queries.csv", q_headers, q_rows)

    # Init progress
    progress = RunProgress(
        total_queries=len(queries),
        total_batches=total_batches,
        status="executing",
    )
    await fm.write_json(run_path / "progress.json", progress.to_dict())

    print(f"Run started: {run_id}", file=sys.stderr)
    print(f"  {len(queries)} queries across {len(locations)} {location_type} in {total_batches} batches", file=sys.stderr)

    # Execute
    batches = list(batch_list(queries, BATCH_SIZE))
    completed = 0
    failed = 0
    total_places = 0
    filter_stats_total = {"input": 0, "output": 0, "filtered": 0}
    dedup_stats_total = {"input": 0, "output": 0, "removed": 0}

    # Set up file logging
    log_handler = logging.FileHandler(run_path / "execution.log")
    log_handler.setLevel(logging.DEBUG)
    log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(log_handler)

    async with SerperClient(api_key) as client:
        for idx, batch in enumerate(batches):
            progress.current_batch = idx
            logger.info(f"Processing batch {idx + 1}/{total_batches}")

            try:
                result = await client.batch_search_places(batch)

                # Save raw response
                await fm.append_jsonl(run_path / "raw" / f"batch-{idx + 1:03d}.jsonl", result)
                completed += 1

                # Extract places
                batch_places = extract_places(result)

                # Apply filtering
                if batch_places:
                    filter_stats_total["input"] += len(batch_places)
                    batch_places, fstats = filter_places(batch_places, filters)
                    filter_stats_total["output"] += len(batch_places)
                    filter_stats_total["filtered"] += fstats.get("filtered_total", 0)

                # Apply dedup
                if batch_places:
                    dedup_stats_total["input"] += len(batch_places)
                    batch_places, dstats = deduplicate_places(batch_places, filters.dedupe_by)
                    dedup_stats_total["output"] += dstats.get("output_count", len(batch_places))
                    dedup_stats_total["removed"] += dstats.get("duplicates_removed", 0)

                # Append to results CSV
                if batch_places:
                    await fm.append_csv_rows(
                        run_path / "results.csv",
                        Place.csv_headers(),
                        [p.to_csv_row() for p in batch_places],
                    )
                    total_places += len(batch_places)

            except SerperAPIError as e:
                logger.error(f"Batch {idx + 1} failed: {e}")
                failed += len(batch)

                # Save error
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

                return {
                    "status": "error",
                    "run_id": run_id,
                    "error": str(e),
                    "failed_batch": idx,
                    "completed_batches": completed,
                    "total_places": total_places,
                }

            # Update progress
            progress.completed_batches = completed
            progress.failed_queries = failed
            progress.last_updated = datetime.now()
            await fm.write_json(run_path / "progress.json", progress.to_dict())

            # Rate limit delay
            if idx < len(batches) - 1:
                await asyncio.sleep(0.5)

            # Progress output
            if (idx + 1) % 5 == 0 or idx == len(batches) - 1:
                print(f"  [{idx + 1}/{total_batches}] {total_places:,} places found", file=sys.stderr)

    # Finalize
    progress.status = "completed" if failed == 0 else "completed_with_errors"
    progress.last_updated = datetime.now()
    await fm.write_json(run_path / "progress.json", progress.to_dict())

    logger.removeHandler(log_handler)
    log_handler.close()

    summary = {
        "status": progress.status,
        "run_id": run_id,
        "run_path": str(run_path),
        "total_queries": len(queries),
        "completed_batches": completed,
        "total_batches": total_batches,
        "failed_queries": failed,
        "total_places": total_places,
        "filtering": filter_stats_total,
        "deduplication": dedup_stats_total,
        "results_file": str(run_path / "results.csv"),
    }

    # Save summary
    await fm.write_json(run_path / "summary.json", summary)

    print(json.dumps(summary, indent=2))
    return summary


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Search for offline businesses via Serper Places API")
    parser.add_argument("--terms", nargs="+", required=True, help="Search terms (e.g., 'dentist' 'plumber')")
    parser.add_argument("--states", nargs="+", required=True, help="US state codes (e.g., CA TX NY)")
    parser.add_argument("--pages", type=int, default=5, help="Pages per query (default: 5)")
    parser.add_argument("--cities", type=int, default=None, help="Limit cities per state (default: all)")
    parser.add_argument("--use-state-level", action="store_true", help="Search at state level instead of city level")
    parser.add_argument("--dry-run", action="store_true", help="Show query count and cost without executing")
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory (default: ./data)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    # Filters
    parser.add_argument("--min-rating", type=float, default=None, help="Minimum rating (0-5)")
    parser.add_argument("--min-reviews", type=int, default=None, help="Minimum review count")
    parser.add_argument("--require-website", action="store_true", default=True, help="Only places with website (default: on)")
    parser.add_argument("--no-require-website", dest="require_website", action="store_false", help="Include places without website")
    parser.add_argument("--require-phone", action="store_true", default=None, help="Only places with phone")
    parser.add_argument("--require-address", action="store_true", default=None, help="Only places with address")
    parser.add_argument("--exclude-keywords", nargs="+", default=None, help="Exclude keywords in title/address")
    parser.add_argument("--dedupe-by", choices=["cid", "website", "both"], default="both", help="Dedup method")

    args = parser.parse_args()

    # Resolve data dir
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        data_dir = Path(__file__).parent.parent / "data"

    if args.verbose:
        setup_logging(logging.DEBUG)
    else:
        setup_logging(logging.INFO)

    api_key = os.getenv("SERPER_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: SERPER_API_KEY not set. Run setup.sh or set in .env", file=sys.stderr)
        sys.exit(1)

    validation = validate_search_inputs(args.states, args.terms, args.pages)
    if validation:
        print(f"Error: {validation}", file=sys.stderr)
        sys.exit(1)

    result = asyncio.run(run_search(args, data_dir, api_key or ""))

    if result.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
