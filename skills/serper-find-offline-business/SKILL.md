---
name: serper-find-offline-business
description: Find offline businesses across US states using Serper Places API. Use when user wants to "find businesses", "search local services", "generate leads", "find offline businesses", "scrape Google Maps", or "search places". Filters, deduplicates, and sends to webhooks.
license: MIT
metadata:
  author: kushagra-gtme
  version: 1.0.0
  category: lead-generation
  tags: [serper, places, business-search, lead-gen]
---

# Find Offline Businesses with Serper Places API

Search for offline businesses across US states using the Serper Places API. This skill walks through an interactive workflow: configure search -> dry run -> execute -> optional webhook delivery.

## Prerequisites

Before first use, ensure setup is complete:

```bash
cd <repo-root>  # the directory containing scripts/ and data/
source venv/bin/activate  # or run: bash setup.sh
```

The `.env` file must contain `SERPER_API_KEY`. If missing, run `bash setup.sh`.

## Execution Behavior

**IMPORTANT:** Once the user provides input at any step, execute the next command immediately — do NOT ask for permission to run. The workflow is designed to be safe at each step (dry runs before real searches, etc.), so no additional confirmation is needed between steps. Only pause for user input when the workflow explicitly asks for it (e.g., picking keywords, confirming dry run cost).

## Workflow

### Step 1: Understand the Request

When the user asks to find businesses, extract:
- **Business type** (e.g., "dentists", "plumbers", "restaurants")
- **Target states** (if mentioned)
- **Any filters** (if mentioned)

If the user only mentions a business type, suggest related keywords from [keyword-suggestions.md](references/keyword-suggestions.md). Present the top 20 related keywords and ask the user to pick which ones to include.

### Step 2: Configure States

If states are not specified, present states sorted by population from [us-states-population.md](references/us-states-population.md). Ask the user to pick states.

After states are selected, determine city scope:
- Ask how many cities per state to target, or if they want state-level search
- State-level gives broader but less specific results
- City-level uses the cities.csv file and gives more targeted results

### Step 3: Configure Filters

Ask the user about filters (present as a checklist):
- Minimum rating (e.g., 4.0+)
- Minimum review count
- Require website (ON by default — recommended for outreach)
- Require phone number
- Require address
- Exclude keywords (e.g., "closed", "temp")
- Dedup method: Google CID, website domain, or both (default: both)

### Step 4: Dry Run

Always run a dry run first to show the cost estimate:

```bash
python scripts/search.py \
  --terms "dentist" "dental clinic" \
  --states CA TX FL \
  --pages 3 \
  --cities 5 \
  --min-rating 4.0 \
  --require-website \
  --dedupe-by both \
  --dry-run
```

Present the output to the user:
- Total queries
- Total batches
- Estimated API credits (1 credit per query)
- Ask for confirmation before proceeding

### Step 5: Execute Search

After user confirms, run the actual search (remove `--dry-run`):

```bash
python scripts/search.py \
  --terms "dentist" "dental clinic" \
  --states CA TX FL \
  --pages 3 \
  --cities 5 \
  --min-rating 4.0 \
  --require-website \
  --dedupe-by both
```

Monitor progress output on stderr. The script outputs a JSON summary to stdout when complete.

### Step 6: Review Results

After search completes, show the user:
- Total places found
- Filtering stats (how many filtered out)
- Dedup stats (how many duplicates removed)
- Run ID and path to results.csv

### Step 7: Webhook (Optional)

Ask the user if they want to send results to a webhook URL.

If yes:
1. Ask for the webhook URL
2. Ask about job titles for the payload — suggest relevant titles from [job-titles-by-industry.md](references/job-titles-by-industry.md) based on the business category. Let the user pick which titles to include.
3. Run webhook delivery in background:

```bash
python scripts/send_webhook.py \
  --run-id <run-id> \
  --webhook-url "https://example.com/webhook" \
  --job-titles "Owner" "Office Manager" "Practice Manager" &
```

4. Inform the user the webhook is running in the background
5. They can check status with: `python scripts/check_status.py --run-id <run-id>`

### Step 8: Save Session Log

After all steps complete, create a `session.md` file in the run folder documenting:
- All decisions made (keywords chosen, states, filters, etc.)
- Dry run results
- Final search results
- Webhook configuration (if used)

```bash
# Write session.md to the run folder
cat > data/runs/<run-id>/session.md << 'EOF'
# Search Session Log

## Configuration
- **Business type**: dentist
- **Keywords**: dentist, dental clinic, dental office
- **States**: CA, TX, FL
- **Cities per state**: 5
- **Pages per query**: 3
- **Filters**: min_rating=4.0, require_website=true, dedupe_by=both

## Dry Run
- Total queries: 225
- Estimated credits: 225

## Results
- Places found: 1,847
- After filtering: 1,203
- After dedup: 989
- Results file: results.csv

## Webhook
- URL: https://example.com/webhook
- Job titles: Owner, Office Manager
- Status: completed (989 sent, 0 failed)
EOF
```

## Error Handling

If a search fails mid-run, the error details are saved to `error.json` in the run folder. Resume with:

```bash
python scripts/resume_search.py --run-id <run-id> --start-batch <failed-batch>
```

## Other Commands

```bash
# List all previous runs
python scripts/list_runs.py

# Check status of a specific run
python scripts/check_status.py --run-id <run-id>
```

## Important Notes

- Always activate the venv before running scripts: `source venv/bin/activate`
- All scripts default to `./data` as the data directory
- Results CSV includes both raw and normalized website URLs
- The `--dry-run` flag makes zero API calls — always use it first
- Webhook delivery runs in the background and writes progress to `webhook.json`
