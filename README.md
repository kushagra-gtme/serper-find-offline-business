# Serper Find Offline Business

Find offline businesses (plumbers, dentists, restaurants, etc.) across US states using the [Serper Places API](https://serper.dev). Includes standalone Python scripts and a Claude Code skill for interactive use.

## Features

- Search by business type across any US states/cities
- Filtering: min rating, require website/phone, exclude keywords
- Deduplication by Google CID, website domain, or both
- URL normalization (raw + normalized stored side-by-side)
- CSV checkpoints after every batch (resume on failure)
- Webhook delivery with job title enrichment
- Dry-run mode to estimate API cost before executing

## Quick Start

```bash
# Clone and setup
git clone https://github.com/kushagra-gtme/serper-find-offline-business.git
cd serper-find-offline-business
bash setup.sh

# Activate environment
source venv/bin/activate

# Dry run (no API calls)
python scripts/search.py --terms "dentist" --states CA TX --pages 1 --dry-run

# Real search
python scripts/search.py --terms "dentist" --states CA --pages 3 --min-rating 4.0

# Check status
python scripts/check_status.py --run-id <run-id>

# Send to webhook
python scripts/send_webhook.py --run-id <run-id> --webhook-url https://your-webhook.com/endpoint

# List all runs
python scripts/list_runs.py
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/search.py` | Main search: generate queries, execute, filter, dedup, save CSV |
| `scripts/send_webhook.py` | Send results to webhook with optional job titles |
| `scripts/check_status.py` | Check progress of a run |
| `scripts/resume_search.py` | Resume a failed search from a specific batch |
| `scripts/list_runs.py` | List all previous runs |

## Run Folder Structure

Each search creates a folder in `data/runs/`:

```
data/runs/20260312-143022--dentist--CA-TX--6cities/
  run.json          # Search configuration
  filters.json      # Filter settings
  queries.csv       # All generated queries
  progress.json     # Execution progress
  results.csv       # Final filtered + deduped results
  webhook.json      # Webhook delivery status
  summary.json      # Final summary stats
  execution.log     # Detailed execution log
  raw/              # Raw API responses (batch-001.jsonl, ...)
```

## Claude Code Skill

Install the skill for interactive use in Claude Code:

```bash
# Copy skill to your Claude skills directory
cp -r skills/serper-find-offline-business ~/.claude/skills/
```

Then use natural language: "find dentists in California and Texas" and the skill will guide you through configuration, dry-run, execution, and optional webhook delivery.

## Configuration

All scripts accept `--data-dir` to customize the data directory. Default is `./data`.

API key is loaded from `.env` file (created by `setup.sh`).

## License

MIT
