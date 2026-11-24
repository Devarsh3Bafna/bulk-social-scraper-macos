#!/usr/bin/env bash
# ==============================================================================
# Bulk Social Media Scraper - macOS Finder Launcher
# Double-click in Finder to launch the scraper!
# ==============================================================================

cd "$(dirname "$0")" || exit 1

printf '\e]2;Bulk Social Media Scraper (macOS)\a'

echo "========================================================================"
echo "🍎  Bulk Social Media Scraper for macOS - Launcher"
echo "========================================================================"

CAN_RUN_PYTHON=false
if command -v python3 &>/dev/null; then
    if python3 -c "import sys" 2>/dev/null; then
        CAN_RUN_PYTHON=true
    fi
fi

if [ "$CAN_RUN_PYTHON" = true ]; then
    if [ -d ".venv" ]; then source ".venv/bin/activate"; fi
    python3 -m scraper.cli --interactive
else
    echo "Starting macOS native Web Dashboard..."
    /usr/bin/ruby server.rb
fi
