# Bulk Social Media Scraper for macOS 🍎🚀

A high-performance, asynchronous bulk social media scraper built specifically for **macOS** (Apple Silicon M1/M2/M3/M4 & Intel). Scrape hundreds of profiles, subreddits, hashtags, and channels concurrently across **Reddit, Twitter / X, Instagram, YouTube, TikTok, Pinterest, and LinkedIn** with zero required API keys.

Features native **macOS Notification Center alerts**, **system audio cues**, **Finder double-clickable launchers**, **glassmorphic Web Dashboard**, **multi-threaded media downloader**, and **macOS LaunchAgent automation**.

---

## ✨ Features

- **Multi-Platform Support**:
  - 🟠 **Reddit**: Subreddits (`hot`, `new`, `top`), user submissions, search queries, gallery images, and video fallback.
  - 🐦 **Twitter / X**: Profiles, timeline tweets, likes, retweets, replies, video/photo attachments.
  - 📷 **Instagram**: User profiles, captions, reels, display images, follower counts, and hashtags.
  - ▶️ **YouTube**: Channel uploads, shorts, search queries, view counts, durations, and high-res thumbnails.
  - 🎵 **TikTok**: Creator videos, hashtags, views, likes, shares, sound metadata, and media links.
  - 📌 **Pinterest**: User boards, high-res pins, descriptions, and repin counts.
  - 💼 **LinkedIn**: Public organization updates, posts, and engagement.
- **Bulk Ingestion Engine**:
  - Import batches from **CSV** (`platform,target,limit,sort`), **JSON**, or **TXT** files.
  - ThreadPool-driven concurrent scraping with configurable worker count.
  - Intelligent rate limiting and exponential backoff retry.
  - Automatic **macOS Safari & Chrome User-Agent rotation**.
- **Data Export & Media Downloader**:
  - Exports cleanly to **CSV (UTF-8-SIG for Numbers & Excel)**, **JSON / JSONL**, **SQLite database**, and an **Apple-style standalone HTML report**.
  - Multi-threaded downloader organizes images and videos into `downloads/<platform>/<target>/`.
- **macOS Native Integrations**:
  - 🔔 **Notification Center**: Native notification banner on job completion with statistics via AppleScript (`osascript`).
  - 🔊 **System Audio**: Native audio chime (`Hero`, `Glass`, `Ping`) upon completion.
  - 🖱️ **Finder Double-Clickable Launchers**: `run_macos.command` for interactive CLI and `run_web_ui.command` for Web Dashboard.
  - ⏰ **LaunchAgent Daemon**: Built-in `launchd` plist to run automated scrapes in the background (e.g. daily at 9:00 AM).
  - ⚡ **Finder Quick Action**: Right-click any CSV or text file in Finder to scrape it instantly.
- **Zero-Dependency Architecture**:
  - Built on Python 3 standard library (`urllib`, `sqlite3`, `http.server`, `concurrent.futures`, `csv`, `json`). Runs cleanly without installing heavy third-party packages, while unlocking optional enhancements when packages in `requirements.txt` are installed.

---

## 📁 Directory Structure

```text
bulk-social-scraper-macos/
├── run_macos.command           # Double-click in Finder to launch CLI menu
├── run_web_ui.command          # Double-click in Finder to open Web UI in Safari/Chrome
├── setup_macos.sh              # One-step macOS setup script (venv, permissions, check tools)
├── requirements.txt            # Optional high-performance enhancements
├── config/
│   ├── settings.json           # User configurations (concurrency, delays, audio, output formats)
│   └── user_agents.txt         # macOS Safari and Chrome desktop User-Agents
├── scraper/
│   ├── cli.py                  # Terminal CLI and Interactive Wizard
│   ├── core/
│   │   ├── base.py             # ScrapedItem unified model & BaseScraper
│   │   ├── session.py          # Resilient HTTP client with rotation & backoff
│   │   ├── exporter.py         # CSV, JSON, SQLite, and HTML report exporters
│   │   ├── downloader.py       # Concurrent media asset downloader
│   │   ├── macos_notifier.py   # macOS Notification Center & afplay audio integration
│   │   └── orchestrator.py     # Bulk batch coordinator
│   ├── platforms/              # Platform scrapers (Reddit, Twitter, Instagram, YouTube, etc.)
│   └── web/                    # Apple-styled Web Dashboard (FastAPI/HTTP server + HTML/CSS/JS)
├── macos/
│   ├── com.bulkscraper.agent.plist   # macOS launchd scheduling service
│   ├── install_launchd_service.sh     # Service manager script
│   └── finder_quick_action.workflow.md# Instructions for Finder context menu
└── samples/
    ├── targets_sample.csv      # Multi-platform sample CSV
    ├── targets_sample.json     # Sample JSON batch configuration
    └── targets_sample.txt      # Line-by-line target list
```

---

## 🚀 Quick Start on macOS

### 1. One-Step Setup
Open Terminal and run the setup script:
```bash
cd /Users/mac/.gemini/antigravity/scratch/bulk-social-scraper-macos
chmod +x setup_macos.sh run_macos.command run_web_ui.command
./setup_macos.sh
```

### 2. Method A: Double-Click in Finder (Easiest)
1. Open the project folder in **Finder**.
2. **Double-click `run_macos.command`** &rarr; Opens Terminal with an interactive menu.
3. Or **double-click `run_web_ui.command`** &rarr; Launches the Web Dashboard in Safari!

### 3. Method B: Command Line (CLI)
Run a bulk batch scrape from a CSV file:
```bash
python3 -m scraper.cli --file samples/targets_sample.csv --export csv,json,sqlite,html
```

Scrape a single target:
```bash
# Reddit subreddit
python3 -m scraper.cli --platform reddit --target technology --limit 25

# YouTube channel or search query
python3 -m scraper.cli --platform youtube --target "search:apple silicon m4 pro" --limit 15

# Twitter / X user
python3 -m scraper.cli --platform twitter --target openai --limit 20

# Download media files too
python3 -m scraper.cli --platform reddit --target apple --download-media
```

Launch the interactive wizard:
```bash
python3 -m scraper.cli --interactive
```

### 4. Method C: macOS Web Dashboard
```bash
python3 -m scraper.cli --web
```
Open **`http://localhost:8501`** in Safari or Google Chrome:
- Add single targets or paste a batch list.
- Adjust item limit and toggle media downloads.
- Real-time progress bar and live metrics.
- Interactive data table with photo lightbox preview.
- 1-Click CSV and JSON downloads.

---

## 📊 Batch Input Formats

### CSV Format (`samples/targets_sample.csv`)
```csv
platform,target,limit,sort
reddit,technology,25,hot
reddit,apple,20,top
youtube,search:macos sonoma,15,relevance
twitter,openai,15,latest
instagram,natgeo,10,latest
```

### JSON Format (`samples/targets_sample.json`)
```json
[
  { "platform": "reddit", "target": "programming", "limit": 20 },
  { "platform": "youtube", "target": "search:apple silicon", "limit": 10 }
]
```

### Plain Text (`samples/targets_sample.txt`)
```text
reddit:technology
reddit:webdev
youtube:search:macos tips
twitter:github
```

---

## ⏰ Automated Scheduling with macOS `launchd`

To run bulk scrapes automatically in the background on macOS without keeping Terminal open:

```bash
# Install and register the LaunchAgent (runs daily at 9:00 AM)
./macos/install_launchd_service.sh install

# Trigger an immediate run
./macos/install_launchd_service.sh run-now

# Check status
./macos/install_launchd_service.sh status

# Remove
./macos/install_launchd_service.sh uninstall
```

Logs are recorded in `/tmp/bulkscraper_launchd.log`.

---

## 🧪 Testing

Run the included test suite:
```bash
python3 -m unittest tests/test_scraper.py
```

Test macOS Notification Center alerts:
```bash
python3 -m scraper.cli --test-notify
```

---

## 🛠️ Configuration (`config/settings.json`)

Customize rate limits, concurrency, audio, and output folders:
```json
{
  "concurrency": 3,
  "request_delay_seconds": 1.5,
  "max_retries": 3,
  "timeout_seconds": 20,
  "enable_macos_notifications": true,
  "sound_effects": true,
  "default_sound": "Glass",
  "completion_sound": "Hero",
  "download_media": false,
  "max_media_per_target": 25,
  "output_formats": ["csv", "json", "sqlite", "html"],
  "output_directory": "output",
  "downloads_directory": "downloads"
}
```
