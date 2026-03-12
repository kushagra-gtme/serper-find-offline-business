#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Serper Find Offline Business - Setup ==="
echo ""

# Create venv
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate and install
echo "Installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# API key
if [ -f ".env" ]; then
    echo ""
    echo ".env already exists. Skipping API key setup."
else
    echo ""
    read -p "Enter your Serper API key (get one at serper.dev): " api_key
    if [ -n "$api_key" ]; then
        echo "SERPER_API_KEY=$api_key" > .env
        echo "API key saved to .env"
    else
        echo "Skipped. Copy .env.template to .env and add your key later."
        cp .env.template .env
    fi
fi

# Ensure data dirs
mkdir -p data/runs

echo ""
echo "Setup complete! Activate the environment with:"
echo "  source venv/bin/activate"
echo ""
echo "Run a dry-run test:"
echo "  python scripts/search.py --terms \"plumber\" --states CA --pages 1 --dry-run"
