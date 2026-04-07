# Serper Find Offline Business

A Python toolkit for finding offline businesses (dentists, plumbers, restaurants, etc.) across US states using the [Serper Places API](https://serper.dev). Includes an interactive [Claude Code](https://claude.ai/claude-code) skill for guided workflows.

## What It Does

Search Google Maps at scale, filter for quality, deduplicate across cities, and deliver results to your CRM — all from the command line or conversational AI.

```
"Find dentists in California and Texas"
  → 540 raw results from Serper Places API
  → 496 after filtering (min 4.0 rating, require website)
  → 219 unique businesses after deduplication (56% dedup rate)
  → CSV output + optional webhook delivery to your CRM
```

## Features

- **Multi-state search** — query by business type across any US states and cities
- **Smart filtering** — min rating, min reviews, require website/phone, exclude keywords
- **Deduplication** — by Google CID, website domain, or both (keeps highest-rated)
- **URL normalization** — raw and normalized URLs stored side-by-side
- **CSV checkpoints** — saved after every batch, resume on failure
- **Dry-run mode** — see query count and estimated API cost before executing
- **Webhook delivery** — send results to any URL with job title enrichment and retry logic
- **Rate limiting** — built-in token bucket prevents API throttling

## Quick Start

```bash
git clone https://github.com/kushagra-gtme/serper-find-offline-business.git
cd serper-find-offline-business
bash setup.sh          # creates venv, installs deps, sets API key
source venv/bin/activate

# Dry run — see cost estimate without making API calls
python scripts/search.py --terms "dentist" --states CA TX --pages 1 --dry-run

# Run a search
python scripts/search.py --terms "dentist" --states CA TX --pages 3 --min-rating 4.0

# Check status of a run
python scripts/check_status.py --run-id <run-id>

# Send results to a webhook
python scripts/send_webhook.py --run-id <run-id> --webhook-url https://your-webhook.com/endpoint

# List all previous runs
python scripts/list_runs.py
```

## Architecture

```
scripts/
  search.py             Main search pipeline
  send_webhook.py       Webhook delivery with retries and rate limiting
  check_status.py       Progress monitoring
  resume_search.py      Resume from a failed batch
  list_runs.py          List all runs with metadata
  lib/
    client.py           Async Serper API client with token bucket rate limiter
    models.py           Typed dataclasses (Query, Place, RunConfig, etc.)
    filters.py          Filtering and deduplication logic
    extract.py          Shared place extraction from API responses
    storage.py          File I/O (JSON, CSV, JSONL)
    locations.py        US state/city mapping and loading
    utils.py            Validation, logging, batching utilities

skills/
  serper-find-offline-business/
    SKILL.md            Interactive Claude Code skill definition
    references/         Keyword suggestions, job titles, state populations

data/
  cities.csv            Top 300+ US cities with state info
  runs/                 Search run output folders (gitignored)
```

## Run Folder Structure

Each search creates a self-contained folder in `data/runs/`:

```
data/runs/20260312-143022--dentist--CA-TX--6cities/
  run.json          Search configuration
  filters.json      Filter settings used
  queries.csv       All generated queries
  progress.json     Execution progress (updated per batch)
  results.csv       Final filtered + deduplicated results
  summary.json      Stats (filtering, dedup, timing)
  execution.log     Detailed execution log
  raw/              Raw API responses (batch-001.jsonl, ...)
```

## Claude Code Skill

Install the skill for interactive, conversational use:

```bash
cp -r skills/serper-find-offline-business ~/.claude/skills/
```

Then use natural language in Claude Code:

```
> find dentists in California and Texas
```

The skill walks you through keyword selection, state/city configuration, dry-run preview, execution, and optional webhook delivery.

## Tech Stack

- **Python 3.11+** with asyncio, aiohttp, aiofiles
- **Serper Places API** (batch endpoint, 100 queries per request)
- **3 dependencies**: `aiohttp`, `aiofiles`, `python-dotenv`

## License

MIT
