"""
Bulk Scraper Orchestrator for macOS
Coordinates multi-platform batch jobs, concurrency, exporter, media downloads, and macOS notifications.
"""

import os
import csv
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional
import logging

from .base import ScrapedItem
from .session import ResilientSession
from .exporter import DataExporter
from .downloader import MediaDownloader
from .macos_notifier import notifier

logger = logging.getLogger("BulkScraper.Orchestrator")


class BulkOrchestrator:
    """Orchestrates bulk social media scraping runs."""

    def __init__(
        self,
        config: Dict[str, Any] = None,
        config_path: str = "config/settings.json",
    ):
        self.config = self._load_config(config, config_path)
        self.session = ResilientSession(
            user_agents_file="config/user_agents.txt",
            proxies=self.config.get("proxies", []),
            timeout=self.config.get("timeout_seconds", 20),
            max_retries=self.config.get("max_retries", 3),
            base_delay=self.config.get("request_delay_seconds", 1.5),
        )
        self.exporter = DataExporter(output_dir=self.config.get("output_directory", "output"))
        self.downloader = MediaDownloader(
            download_dir=self.config.get("downloads_directory", "downloads"),
            max_workers=5,
            session=self.session,
        )
        self.notifications_enabled = self.config.get("enable_macos_notifications", True)

    def _load_config(self, custom_config: Dict[str, Any] = None, path: str = "config/settings.json") -> Dict[str, Any]:
        default = {
            "concurrency": 3,
            "request_delay_seconds": 1.5,
            "max_retries": 3,
            "timeout_seconds": 20,
            "enable_macos_notifications": True,
            "sound_effects": True,
            "download_media": False,
            "max_media_per_target": 25,
            "output_formats": ["csv", "json", "sqlite", "html"],
            "output_directory": "output",
            "downloads_directory": "downloads",
            "proxies": [],
        }
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    file_conf = json.load(f)
                    default.update(file_conf)
            except Exception as e:
                logger.warning("Could not read config file %s: %s", path, e)

        if custom_config:
            default.update(custom_config)
        return default

    def parse_batch_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Parses a target batch file (.csv, .json, or .txt)."""
        from ..platforms import detect_platform_from_url
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Target batch file not found: {filepath}")

        targets = []
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".csv":
            with open(filepath, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    plat = row.get("platform") or detect_platform_from_url(row.get("target", ""))
                    tgt = row.get("target") or row.get("url") or row.get("username")
                    if tgt:
                        targets.append({
                            "platform": (plat or "reddit").lower(),
                            "target": tgt,
                            "limit": int(row.get("limit") or 25),
                            "sort": row.get("sort", "hot"),
                        })

        elif ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        plat = item.get("platform") or detect_platform_from_url(item.get("target", ""))
                        tgt = item.get("target") or item.get("url")
                        if tgt:
                            targets.append({
                                "platform": (plat or "reddit").lower(),
                                "target": tgt,
                                "limit": int(item.get("limit", 25)),
                                "sort": item.get("sort", "hot"),
                            })

        elif ext in (".txt", ""):
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # format can be: platform:target (e.g. reddit:technology) or a URL
                    if ":" in line and not line.startswith("http"):
                        parts = line.split(":", 1)
                        plat, tgt = parts[0].strip(), parts[1].strip()
                    else:
                        plat = detect_platform_from_url(line) or "reddit"
                        tgt = line

                    targets.append({
                        "platform": plat.lower(),
                        "target": tgt,
                        "limit": 25,
                        "sort": "hot",
                    })

        return targets

    def scrape_single_target(self, task: Dict[str, Any]) -> List[ScrapedItem]:
        """Executes a scrape for one target specification."""
        from ..platforms import get_scraper_for_platform, detect_platform_from_url
        platform = task.get("platform", "").lower()
        target = task.get("target", "")
        limit = task.get("limit", 25)
        sort = task.get("sort", "hot")

        if not platform:
            platform = detect_platform_from_url(target) or "reddit"

        try:
            scraper = get_scraper_for_platform(
                platform,
                session=self.session,
                delay=self.config.get("request_delay_seconds", 1.5),
            )
            return scraper.scrape(target, limit=limit, sort=sort)
        except Exception as e:
            logger.error("Failed scraping target '%s' on %s: %s", target, platform, e)
            return []

    def run_bulk(
        self,
        targets: List[Dict[str, Any]],
        download_media: Optional[bool] = None,
        export_formats: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Runs bulk scraping on a list of targets with concurrency, exports results,
        downloads media, and fires macOS alerts.
        """
        start_time = time.time()
        total_targets = len(targets)
        concurrency = self.config.get("concurrency", 3)
        should_download = download_media if download_media is not None else self.config.get("download_media", False)
        formats = export_formats or self.config.get("output_formats", ["csv", "json", "sqlite", "html"])

        all_items: List[ScrapedItem] = []
        completed_count = 0
        target_results = {}

        logger.info("Initiating bulk scrape for %d targets with concurrency %d", total_targets, concurrency)

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_task = {
                executor.submit(self.scrape_single_target, task): task for task in targets
            }

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                task_name = f"{task.get('platform')}:{task.get('target')}"
                completed_count += 1

                try:
                    items = future.result()
                    all_items.extend(items)
                    target_results[task_name] = {"success": True, "count": len(items)}
                except Exception as e:
                    target_results[task_name] = {"success": False, "error": str(e)}

                if progress_callback:
                    progress_callback(completed_count, total_targets, target_results[task_name])

        elapsed = time.time() - start_time

        # Export data
        exported_files = self.exporter.export_all(all_items, formats=formats)

        # Download media if enabled
        media_report = {}
        if should_download and all_items:
            media_report = self.downloader.download_items_media(
                all_items, max_per_target=self.config.get("max_media_per_target", 25)
            )

        # Trigger macOS Notification
        if self.notifications_enabled:
            item_count = len(all_items)
            msg = f"Gathered {item_count} items across {total_targets} targets in {elapsed:.1f}s."
            if should_download and media_report.get("successful"):
                msg += f" {media_report['successful']} media files saved."

            notifier.notify(
                title="Bulk Scraper Finished 🚀",
                message=msg,
                subtitle="macOS Social Media Scraper",
                sound="Hero",
            )
            if self.config.get("sound_effects", True):
                notifier.play_sound("Hero")

        summary = {
            "total_targets": total_targets,
            "total_items_scraped": len(all_items),
            "elapsed_seconds": round(elapsed, 2),
            "target_results": target_results,
            "exported_files": exported_files,
            "media_report": media_report,
            "items": all_items,
        }

        return summary
