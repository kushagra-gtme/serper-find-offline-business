# Serper Find Offline Business — One-Pager

## What It Does

A Python toolkit + Claude Code skill that finds offline businesses (dentists, plumbers, restaurants, etc.) across US states using the Serper Places API. Think of it as a programmable Google Maps scraper with built-in filtering, deduplication, and webhook delivery.

## The Problem

Finding local business leads at scale requires:
- Writing custom API integrations
- Handling rate limits and failures
- Deduplicating results across cities
- Normalizing messy data (URLs, addresses)
- Delivering results to CRMs or outreach tools

## The Solution

**5 standalone Python scripts** wrapped by an **interactive Claude Code skill** that walks you through every step:

```
User: "Find dentists in California and Texas"
  → Skill suggests 20 related keywords (dental clinic, orthodontist, ...)
  → User picks keywords, states, cities, filters
  → Dry run shows: "225 queries, ~$2.25 in API credits"
  → User confirms → search runs with live progress
  → 190 unique qualified businesses saved to CSV
  → Optional: webhook sends each result to your CRM with job titles
```

## Key Numbers (Real Test Run)

| Metric | Value |
|--------|-------|
| Search terms | "dentist", "dental clinic" |
| States | CA, TX (3 cities each) |
| Raw results | 240 places |
| After min 4.0 rating filter | 225 |
| After deduplication | **190 unique businesses** |
| API credits used | 24 |
| Time to complete | ~4 seconds |

## Features

- **Smart filtering**: min rating, require website/phone, exclude keywords
- **Deduplication**: by Google CID, website domain, or both
- **URL normalization**: raw and normalized URLs stored side-by-side
- **Checkpoints**: CSV saved after every batch — resume on failure
- **Dry-run mode**: see cost before spending API credits
- **Webhook delivery**: send results to any URL with job title enrichment
- **Session logs**: every decision stored in the run folder

## Architecture

```
scripts/
  search.py          ← Main search pipeline
  send_webhook.py    ← Webhook delivery with job titles
  check_status.py    ← Progress monitoring
  resume_search.py   ← Resume from failed batch
  list_runs.py       ← List all runs
  lib/               ← Shared modules (client, models, filters, storage)

skills/
  serper-find-offline-business/
    SKILL.md          ← Interactive Claude Code skill
    references/       ← Keyword suggestions, state populations, job titles
```

## Run Folder Structure

Each search creates a self-contained folder:
```
data/runs/20260312-181559--dentist--CA-TX--6cities/
  run.json        results.csv      progress.json
  filters.json    queries.csv      summary.json
  webhook.json    execution.log    raw/
```

## How to Use

**As scripts:**
```bash
bash setup.sh
source venv/bin/activate
python scripts/search.py --terms "plumber" --states CA TX NY --pages 3 --min-rating 4.0
```

**As a Claude Code skill:**
```
> find offline dentists in the top 5 US states
```
The skill handles everything interactively.

## Tech Stack

- Python 3.11+ (asyncio, aiohttp, aiofiles)
- Serper Places API (batch endpoint, 100 queries/batch)
- Claude Code Skills (SKILL.md + reference files)
- No framework dependencies — just 3 pip packages

## Links

- **Repo**: [github.com/kushagra-gtme/serper-find-offline-business](https://github.com/kushagra-gtme/serper-find-offline-business)
- **API**: [serper.dev](https://serper.dev)
- **License**: MIT
