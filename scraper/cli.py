"""
Command Line Interface & Interactive Terminal Wizard for macOS Bulk Social Media Scraper
"""

import sys
import os
import argparse
import time
from typing import List, Dict, Any

from .core.orchestrator import BulkOrchestrator
from .core.macos_notifier import notifier
from .platforms import SCRAPER_REGISTRY

# ANSI Color codes for macOS Terminal / iTerm2 / Warp
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    banner = f"""
{CYAN}{BOLD}========================================================================{RESET}
{CYAN}{BOLD}      🍎  BULK SOCIAL MEDIA SCRAPER FOR macOS  🚀{RESET}
{DIM}  Multi-Platform • Native macOS Notifications • Resilient Async Engine{RESET}
{CYAN}========================================================================{RESET}
    """
    print(banner)


def run_interactive_wizard():
    """Guided terminal menu for macOS users."""
    print_banner()
    print(f"{BOLD}Choose an action:{RESET}")
    print(f"  {CYAN}1{RESET}) 🚀 Run Bulk Scraping with Sample Batch File (samples/targets_sample.csv)")
    print(f"  {CYAN}2{RESET}) 🎯 Scrape a Single Target (Reddit, Twitter, Instagram, YouTube, TikTok, Pinterest)")
    print(f"  {CYAN}3{RESET}) 📂 Select a Custom Batch File (.csv, .json, or .txt)")
    print(f"  {CYAN}4{RESET}) 🌐 Launch macOS Web Dashboard (Safari / Chrome)")
    print(f"  {CYAN}5{RESET}) 🔔 Test macOS Notification Center & System Sounds")
    print(f"  {CYAN}6{RESET}) ❌ Exit\n")

    try:
        choice = input(f"{BOLD}Enter option [1-6]: {RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        return

    if choice == "1":
        sample_path = "samples/targets_sample.csv"
        if not os.path.exists(sample_path):
            sample_path = os.path.join(os.path.dirname(__file__), "..", "samples", "targets_sample.csv")
        execute_batch_run(sample_path)

    elif choice == "2":
        print(f"\n{BOLD}Supported Platforms:{RESET} {', '.join(SCRAPER_REGISTRY.keys())}")
        plat = input(f"{BOLD}Platform [reddit]: {RESET}").strip() or "reddit"
        target = input(f"{BOLD}Target (username, subreddit, or search query): {RESET}").strip()
        if not target:
            print(f"{RED}Target cannot be empty.{RESET}")
            return
        limit_str = input(f"{BOLD}Limit per target [15]: {RESET}").strip() or "15"
        limit = int(limit_str) if limit_str.isdigit() else 15
        dl_media = input(f"{BOLD}Download media files? (y/N): {RESET}").strip().lower() == "y"

        orchestrator = BulkOrchestrator()
        task = [{"platform": plat, "target": target, "limit": limit, "sort": "hot"}]
        print(f"\n{YELLOW}Scraping {plat}:{target}...{RESET}")
        summary = orchestrator.run_bulk(task, download_media=dl_media)
        display_summary(summary)

    elif choice == "3":
        file_path = input(f"{BOLD}Enter path to batch file: {RESET}").strip()
        if not os.path.exists(file_path):
            print(f"{RED}File not found: {file_path}{RESET}")
            return
        execute_batch_run(file_path)

    elif choice == "4":
        from .web.app import launch_web_server
        launch_web_server()

    elif choice == "5":
        print(f"\n{YELLOW}Testing macOS Notification Center alert...{RESET}")
        ok = notifier.notify(
            title="Bulk Scraper macOS",
            message="Notification Center test successful! System ready.",
            sound="Hero",
        )
        notifier.play_sound("Hero")
        if ok:
            print(f"{GREEN}✓ Notification sent successfully to macOS Notification Center.{RESET}")
        else:
            print(f"{YELLOW}Sent fallback notification alert.{RESET}")

    elif choice == "6":
        print("Goodbye!")
        return


def execute_batch_run(
    batch_file: str,
    download_media: bool = False,
    export_formats: List[str] = None,
    concurrency: int = 3,
):
    print(f"\n{CYAN}Loading targets from: {batch_file}...{RESET}")
    orchestrator = BulkOrchestrator(config={"concurrency": concurrency})
    try:
        targets = orchestrator.parse_batch_file(batch_file)
    except Exception as e:
        print(f"{RED}Error parsing file: {e}{RESET}")
        return

    print(f"{GREEN}Found {len(targets)} targets to scrape.{RESET}\n")
    for idx, t in enumerate(targets, 1):
        print(f"  {idx}. [{t['platform'].upper()}] {t['target']} (limit={t['limit']})")

    confirm = input(f"\n{BOLD}Proceed with bulk scraping? (Y/n): {RESET}").strip().lower()
    if confirm in ("n", "no"):
        print("Aborted.")
        return

    def on_progress(done, total, result):
        status_sym = f"{GREEN}✓{RESET}" if result.get("success") else f"{RED}✗{RESET}"
        count = result.get("count", 0)
        print(f"[{done}/{total}] {status_sym} Scraped {count} items")

    print(f"\n{YELLOW}Starting bulk scrape...{RESET}")
    summary = orchestrator.run_bulk(
        targets,
        download_media=download_media,
        export_formats=export_formats,
        progress_callback=on_progress,
    )
    display_summary(summary)


def display_summary(summary: Dict[str, Any]):
    print(f"\n{GREEN}{BOLD}========================================================================{RESET}")
    print(f"{GREEN}{BOLD}                 SCRAPING COMPLETED SUCCESSFULLY 🎉{RESET}")
    print(f"{GREEN}{BOLD}========================================================================{RESET}")
    print(f"  {BOLD}Total Items Scraped:{RESET} {summary['total_items_scraped']}")
    print(f"  {BOLD}Elapsed Time:{RESET}        {summary['elapsed_seconds']} seconds")

    print(f"\n{BOLD}Exported Files:{RESET}")
    for fmt, path in summary.get("exported_files", {}).items():
        if path:
            print(f"  • {BOLD}{fmt.upper():<7}{RESET} -> {CYAN}{path}{RESET}")

    media_report = summary.get("media_report", {})
    if media_report and media_report.get("total_tasks"):
        print(f"\n{BOLD}Media Downloads:{RESET}")
        print(f"  • Downloaded: {media_report.get('successful', 0)} of {media_report.get('total_tasks', 0)} files")
        print(f"  • Destination: {CYAN}downloads/{RESET}")

    # macOS tip to open HTML report in Safari
    html_report = summary.get("exported_files", {}).get("html")
    if html_report:
        print(f"\n{YELLOW}Tip:{RESET} Open the report in Safari with:")
        print(f"  {DIM}open \"{html_report}\"{RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Bulk Social Media Scraper for macOS - Twitter, Reddit, Instagram, YouTube, TikTok, Pinterest",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-f", "--file", help="Path to batch target file (.csv, .json, .txt)")
    parser.add_argument("-p", "--platform", help="Platform name (reddit, twitter, instagram, youtube, tiktok, pinterest, linkedin)")
    parser.add_argument("-t", "--target", help="Single target (handle, subreddit, channel, search query)")
    parser.add_argument("-l", "--limit", type=int, default=25, help="Maximum items to scrape per target (default: 25)")
    parser.add_argument("-e", "--export", default="csv,json,sqlite,html", help="Comma-separated export formats (default: csv,json,sqlite,html)")
    parser.add_argument("-m", "--download-media", action="store_true", help="Download attached images and videos")
    parser.add_argument("-c", "--concurrency", type=int, default=3, help="Concurrent workers (default: 3)")
    parser.add_argument("-w", "--web", action="store_true", help="Launch the local Web Dashboard in browser")
    parser.add_argument("-i", "--interactive", action="store_true", help="Launch interactive guided terminal menu")
    parser.add_argument("--test-notify", action="store_true", help="Test macOS Notification Center alert")

    args = parser.parse_args()

    if args.test_notify:
        print("Testing macOS notification...")
        notifier.notify("Bulk Scraper macOS", "Notification Center works perfectly!", sound="Hero")
        notifier.play_sound("Hero")
        print("Done.")
        return

    if args.web:
        from .web.app import launch_web_server
        launch_web_server()
        return

    if args.interactive or (not args.file and not args.target):
        run_interactive_wizard()
        return

    export_formats = [fmt.strip().lower() for fmt in args.export.split(",") if fmt.strip()]
    orchestrator = BulkOrchestrator(config={"concurrency": args.concurrency})

    if args.file:
        targets = orchestrator.parse_batch_file(args.file)
        summary = orchestrator.run_bulk(
            targets,
            download_media=args.download_media,
            export_formats=export_formats,
        )
        display_summary(summary)

    elif args.target:
        platform = args.platform or "reddit"
        tasks = [{"platform": platform, "target": args.target, "limit": args.limit}]
        print(f"Scraping [{platform.upper()}] target: {args.target} (limit={args.limit})...")
        summary = orchestrator.run_bulk(
            tasks,
            download_media=args.download_media,
            export_formats=export_formats,
        )
        display_summary(summary)


if __name__ == "__main__":
    main()
