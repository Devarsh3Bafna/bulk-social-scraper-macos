#!/usr/bin/env bash
# ==============================================================================
# Helper to install or uninstall the macOS LaunchAgent background scraper service
# ==============================================================================

SERVICE_NAME="com.bulkscraper.agent"
PLIST_SRC="$(dirname "$0")/com.bulkscraper.agent.plist"
USER_LAUNCHAGENTS="$HOME/Library/LaunchAgents"
DEST_PLIST="$USER_LAUNCHAGENTS/${SERVICE_NAME}.plist"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

ACTION="${1:-status}"

case "$ACTION" in
    install)
        echo "Installing macOS LaunchAgent..."
        mkdir -p "$USER_LAUNCHAGENTS"

        # Substitute $SCRAPER_DIR with actual absolute project path
        sed "s|\$SCRAPER_DIR|$PROJECT_DIR|g" "$PLIST_SRC" > "$DEST_PLIST"
        
        launchctl unload "$DEST_PLIST" 2>/dev/null || true
        launchctl load "$DEST_PLIST"
        echo "✓ LaunchAgent installed and loaded at: $DEST_PLIST"
        echo "The scraper will run automatically every day at 9:00 AM."
        ;;
    uninstall)
        echo "Uninstalling LaunchAgent..."
        launchctl unload "$DEST_PLIST" 2>/dev/null || true
        rm -f "$DEST_PLIST"
        echo "✓ LaunchAgent removed."
        ;;
    run-now)
        echo "Triggering immediate background run via launchctl..."
        launchctl start "$SERVICE_NAME"
        echo "Check log file: cat /tmp/bulkscraper_launchd.log"
        ;;
    status|*)
        echo "LaunchAgent Service Status:"
        if [ -f "$DEST_PLIST" ]; then
            echo "Installed at: $DEST_PLIST"
            launchctl list | grep "$SERVICE_NAME" || echo "(Not currently running)"
        else
            echo "Not installed."
            echo "Usage: $0 [install | uninstall | run-now | status]"
        fi
        ;;
esac
