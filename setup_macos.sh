#!/usr/bin/env bash
# ==============================================================================
# Setup & Installation Script for Bulk Social Media Scraper on macOS
# Compatible with macOS Sequoia, Sonoma, Ventura, Monterey (Apple Silicon & Intel)
# ==============================================================================

set -e
cd "$(dirname "$0")"

GREEN="\033[92m"
CYAN="\033[96m"
YELLOW="\033[93m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "${CYAN}${BOLD}========================================================================${RESET}"
echo -e "${CYAN}${BOLD}       🍎 Setting Up Bulk Social Media Scraper for macOS${RESET}"
echo -e "${CYAN}${BOLD}========================================================================${RESET}"

ARCH=$(uname -m)
OS_VER=$(sw_vers -productVersion 2>/dev/null || echo "macOS")
echo -e "Detected: ${BOLD}macOS ${OS_VER} (${ARCH})${RESET}\n"

# 1. Check Xcode Command Line Tools
echo -e "${BOLD}[1/5] Checking macOS developer tools...${RESET}"
if ! xcode-select -p &>/dev/null; then
    echo -e "${YELLOW}Xcode Command Line Tools not detected.${RESET}"
    echo "Prompting macOS to install Command Line Tools..."
    xcode-select --install 2>/dev/null || true
    echo -e "${YELLOW}Please complete the prompt on your screen if one appeared, then re-run this script.${RESET}\n"
else
    echo -e "${GREEN}✓ Xcode Command Line Tools are active.${RESET}"
fi

# 2. Check for Python 3
echo -e "\n${BOLD}[2/5] Checking Python 3 runtime...${RESET}"
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif [ -f "/opt/homebrew/bin/python3" ]; then
    PYTHON_CMD="/opt/homebrew/bin/python3"
elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_CMD="/usr/local/bin/python3"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${YELLOW}Python 3 not found.${RESET}"
    if command -v brew &>/dev/null; then
        echo "Installing Python 3 via Homebrew..."
        brew install python
        PYTHON_CMD="python3"
    else
        echo "Please install Python 3 from https://www.python.org/downloads/macos/ or install Homebrew."
        exit 1
    fi
else
    PY_VER=$($PYTHON_CMD --version 2>&1 || echo "Python 3")
    echo -e "${GREEN}✓ Found ${PY_VER}${RESET}"
fi

# 3. Create virtual environment
echo -e "\n${BOLD}[3/5] Setting up Python virtual environment (.venv)...${RESET}"
if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv 2>/dev/null || python3 -m venv .venv
    echo -e "${GREEN}✓ Created virtual environment at .venv${RESET}"
else
    echo -e "${GREEN}✓ Existing .venv found.${RESET}"
fi

source .venv/bin/activate
pip install --upgrade pip --quiet 2>/dev/null || true

# 4. Install dependencies
echo -e "\n${BOLD}[4/5] Installing optional high-performance libraries...${RESET}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt --quiet 2>/dev/null || echo -e "${YELLOW}Standard library mode active (zero external dependencies needed).${RESET}"
    echo -e "${GREEN}✓ Dependencies configured.${RESET}"
fi

# 5. Fix executable permissions
echo -e "\n${BOLD}[5/5] Granting execute permissions to macOS launchers...${RESET}"
chmod +x run_macos.command 2>/dev/null || true
chmod +x run_web_ui.command 2>/dev/null || true
chmod +x setup_macos.sh 2>/dev/null || true
chmod +x macos/install_launchd_service.sh 2>/dev/null || true
echo -e "${GREEN}✓ Permissions updated for Finder .command files.${RESET}"

# Verify macOS Notifications & Audio
echo -e "\n${CYAN}Testing macOS Notification Center integration...${RESET}"
osascript -e 'display notification "Setup completed successfully! Ready to scrape." with title "Bulk Scraper macOS" subtitle "Ready" sound name "Hero"' 2>/dev/null || true

echo -e "\n${GREEN}${BOLD}========================================================================${RESET}"
echo -e "${GREEN}${BOLD}                  SETUP COMPLETED SUCCESSFULLY! 🎉${RESET}"
echo -e "${GREEN}${BOLD}========================================================================${RESET}"
echo -e "You can now run the scraper in 3 ways:"
echo -e "  1. ${BOLD}Double-click${RESET} ${CYAN}run_macos.command${RESET} in Finder for Interactive Terminal mode"
echo -e "  2. ${BOLD}Double-click${RESET} ${CYAN}run_web_ui.command${RESET} in Finder for the Web Dashboard in Safari"
echo -e "  3. Run from Terminal: ${CYAN}./run_macos.command${RESET} or ${CYAN}python3 -m scraper.cli --file samples/targets_sample.csv${RESET}\n"
