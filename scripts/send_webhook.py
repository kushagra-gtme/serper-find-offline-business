#!/usr/bin/env python3
"""
Send search results to a webhook URL.

Usage:
    python scripts/send_webhook.py --run-id <id> --webhook-url <url>
    python scripts/send_webhook.py --run-id <id> --webhook-url <url> --job-titles "Owner" "Manager"
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
import aiohttp

sys.path.insert(0, str(Path(__file__).parent))

from lib.storage import FileManager
from lib.filters import normalize_url
from lib.utils import setup_logging, sanitize_run_id, validate_webhook_url


async def send_webhook(
    run_id: str,
    webhook_url: str,
    data_dir: Path,
    batch_size: int = 50,
    max_retries: int = 3,
    job_titles: list = None,
) -> dict:
    logger = logging.getLogger("serper")
    fm = FileManager(data_dir)
    run_path = fm.get_run_path(run_id)

    if not run_path.exists():
        return {"status": "error", "message": f"Run {run_id} not found"}

    results_file = run_path / "results.csv"
    if not results_file.exists():
        return {"status": "error", "message": "results.csv not found. Run search first."}

    headers_csv, rows = fm.read_csv(results_file)

    if not rows:
        return {"status": "skipped", "message": "No results to send"}

    # Init progress
    progress = {
        "status": "sending",
        "started_at": datetime.now().isoformat(),
        "total": len(rows),
        "sent": 0,
        "failed": 0,
        "retried": 0,
    }
    await fm.write_json(run_path / "webhook.json", progress)

    logger.info(f"Sending {len(rows)} records to webhook")

    sent = 0
    failed = 0
    retried = 0
    failed_records = []
    semaphore = asyncio.Semaphore(batch_size)

    async def send_record(idx: int, row: list) -> tuple:
        nonlocal retried
        payload = {headers_csv[i]: row[i] for i in range(min(len(headers_csv), len(row)))}

        # Add job titles if provided
        if job_titles:
            payload["target_job_titles"] = job_titles

        async with semaphore:
            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            webhook_url,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as resp:
                            if resp.status in (200, 201, 202):
                                if attempt > 0:
                                    retried += 1
                                return (idx, True, None)
                            elif resp.status >= 500 and attempt < max_retries - 1:
                                await asyncio.sleep(2 ** attempt)
                                continue
                            else:
                                return (idx, False, f"HTTP {resp.status}")
                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return (idx, False, "Timeout")
                except Exception as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return (idx, False, str(e))
            return (idx, False, "Max retries exceeded")

    # Process in batches
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        tasks = [send_record(i + j, row) for j, row in enumerate(batch)]
        results = await asyncio.gather(*tasks)

        for idx, success, error in results:
            if success:
                sent += 1
            else:
                failed += 1
                failed_records.append({"index": idx, "error": error})

        progress["sent"] = sent
        progress["failed"] = failed
        progress["retried"] = retried
        await fm.write_json(run_path / "webhook.json", progress)

        if (i + batch_size) % 200 == 0 or i + batch_size >= len(rows):
            print(f"  [{min(i + batch_size, len(rows))}/{len(rows)}] sent={sent} failed={failed}", file=sys.stderr)

        await asyncio.sleep(0.1)

    # Finalize
    progress["status"] = "completed" if failed == 0 else "completed_with_errors"
    progress["completed_at"] = datetime.now().isoformat()
    progress["success_rate"] = f"{sent / len(rows) * 100:.1f}%"
    if failed_records:
        progress["failed_records"] = failed_records[:100]

    await fm.write_json(run_path / "webhook.json", progress)

    print(json.dumps(progress, indent=2))
    return progress


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Send search results to webhook")
    parser.add_argument("--run-id", required=True, help="Run ID")
    parser.add_argument("--webhook-url", required=True, help="Webhook URL")
    parser.add_argument("--batch-size", type=int, default=50, help="Concurrent requests (default: 50)")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries per record (default: 3)")
    parser.add_argument("--job-titles", nargs="+", default=None, help="Job titles to include in payload")
    parser.add_argument("--data-dir", type=str, default=None, help="Data directory")

    args = parser.parse_args()

    setup_logging()

    # Validate
    err = sanitize_run_id(args.run_id)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    err = validate_webhook_url(args.webhook_url)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    data_dir = Path(args.data_dir) if args.data_dir else Path(__file__).parent.parent / "data"

    result = asyncio.run(send_webhook(
        run_id=args.run_id,
        webhook_url=args.webhook_url,
        data_dir=data_dir,
        batch_size=args.batch_size,
        max_retries=args.max_retries,
        job_titles=args.job_titles,
    ))

    if result.get("status") == "error":
        sys.exit(1)


if __name__ == "__main__":
    main()
