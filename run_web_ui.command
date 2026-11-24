#!/usr/bin/env bash
# ==============================================================================
# Bulk Social Media Scraper - macOS Web Dashboard Launcher
# Works out of the box on every Mac (Auto-detects Python or Built-in Ruby)
# ==============================================================================

cd "$(dirname "$0")" || exit 1

printf '\e]2;Bulk Social Media Scraper - Web UI\a'

echo "========================================================================"
echo "🍎 Starting Bulk Social Media Scraper Web Dashboard on macOS..."
echo "========================================================================"

# Test if Python 3 works without Xcode developer tools prompt
CAN_RUN_PYTHON=false
if command -v python3 &>/dev/null; then
    if python3 -c "import sys" 2>/dev/null; then
        CAN_RUN_PYTHON=true
    fi
fi

if [ "$CAN_RUN_PYTHON" = true ]; then
    echo "⚡ Using Python 3 engine..."
    if [ -d ".venv" ]; then source ".venv/bin/activate"; fi
    python3 -m scraper.cli --web
else
    echo "⚡ Using macOS native system engine (/usr/bin/ruby)..."
    echo "No Xcode or extra tools required!"
    /usr/bin/ruby server.rb
fi
