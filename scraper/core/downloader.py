"""
Media Downloader for macOS Bulk Social Media Scraper
Downloads photos, videos, thumbnails, and attachments concurrently into organized folders.
"""

import os
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
import logging
from .base import ScrapedItem
from .session import ResilientSession

logger = logging.getLogger("BulkScraper.Downloader")


class MediaDownloader:
    """Manages concurrent downloads of scraped media assets."""

    def __init__(self, download_dir: str = "downloads", max_workers: int = 5, session: ResilientSession = None):
        self.download_dir = download_dir
        self.max_workers = max_workers
        self.session = session or ResilientSession()
        os.makedirs(self.download_dir, exist_ok=True)

    def _sanitize_name(self, name: str) -> str:
        """Sanitizes strings for safe macOS filesystem folder/file naming."""
        clean = re.sub(r'[\\/*?:"<>|]', "", name)
        clean = clean.strip().replace(" ", "_")
        return clean[:50] or "unnamed"

    def _guess_extension(self, url: str, content_type: str = "") -> str:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".m4v", ".webm"):
            return ext

        # Infer from content type
        if "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
        elif "png" in content_type:
            return ".png"
        elif "webp" in content_type:
            return ".webp"
        elif "gif" in content_type:
            return ".gif"
        elif "mp4" in content_type:
            return ".mp4"
        elif "webm" in content_type:
            return ".webm"
        return ".jpg"

    def download_url(self, url: str, target_dir: str, filename_prefix: str) -> Tuple[bool, str]:
        """Downloads a single URL and saves it to target_dir."""
        try:
            res = self.session.request(url, method="GET")
            if res.get("status") != 200 or not res.get("raw_bytes"):
                return False, f"Failed HTTP {res.get('status')}"

            content_type = res.get("headers", {}).get("Content-Type", "")
            ext = self._guess_extension(url, content_type)
            safe_prefix = self._sanitize_name(filename_prefix)
            dest_file = os.path.join(target_dir, f"{safe_prefix}{ext}")

            # Avoid overwrite collision
            counter = 1
            base_dest = os.path.join(target_dir, safe_prefix)
            while os.path.exists(dest_file):
                dest_file = f"{base_dest}_{counter}{ext}"
                counter += 1

            with open(dest_file, "wb") as f:
                f.write(res["raw_bytes"])

            return True, dest_file
        except Exception as e:
            return False, str(e)

    def download_items_media(
        self, items: List[ScrapedItem], max_per_target: int = 50
    ) -> Dict[str, Any]:
        """
        Downloads media for a collection of ScrapedItems.
        Returns a summary report with paths and counts.
        """
        tasks = []
        target_counts = {}

        for item in items:
            if not item.media_urls:
                continue

            target_key = f"{item.platform}_{item.target}"
            curr_count = target_counts.get(target_key, 0)
            if curr_count >= max_per_target:
                continue

            folder = os.path.join(
                self.download_dir,
                self._sanitize_name(item.platform),
                self._sanitize_name(item.target),
            )
            os.makedirs(folder, exist_ok=True)

            for idx, media_url in enumerate(item.media_urls):
                if curr_count >= max_per_target:
                    break
                target_counts[target_key] = target_counts.get(target_key, 0) + 1
                curr_count += 1
                prefix = f"{item.id}_{idx+1}"
                tasks.append((media_url, folder, prefix, item.platform, item.target))

        total_downloads = len(tasks)
        if total_downloads == 0:
            return {"total_tasks": 0, "successful": 0, "failed": 0, "downloaded_files": []}

        successful = 0
        failed = 0
        downloaded_files = []

        logger.info("Starting concurrent download of %d media files...", total_downloads)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_info = {
                executor.submit(self.download_url, url, folder, prefix): (url, platform, target)
                for (url, folder, prefix, platform, target) in tasks
            }

            for future in as_completed(future_to_info):
                url, platform, target = future_to_info[future]
                try:
                    ok, result = future.result()
                    if ok:
                        successful += 1
                        downloaded_files.append(result)
                    else:
                        failed += 1
                        logger.debug("Failed media download %s: %s", url, result)
                except Exception as e:
                    failed += 1
                    logger.debug("Exception downloading %s: %s", url, e)

        logger.info(
            "Media download complete: %d succeeded, %d failed out of %d.",
            successful,
            failed,
            total_downloads,
        )
        return {
            "total_tasks": total_downloads,
            "successful": successful,
            "failed": failed,
            "downloaded_files": downloaded_files,
        }
