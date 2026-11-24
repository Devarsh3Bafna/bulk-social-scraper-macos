"""
TikTok Scraper for macOS Bulk Scraper
Scrapes public TikTok creator profiles, hashtags, video statistics, and media URLs.
"""

from typing import List
import json
import re
import urllib.parse
from datetime import datetime
import logging
from ..core.base import BaseScraper, ScrapedItem

logger = logging.getLogger("BulkScraper.TikTok")


class TikTokScraper(BaseScraper):
    platform_name = "tiktok"

    def _extract_username(self, target: str) -> str:
        clean = self.clean_target(target)
        if "tiktok.com/" in clean:
            parsed = urllib.parse.urlparse(clean if "://" in clean else f"https://{clean}")
            parts = parsed.path.strip("/").split("/")
            for p in parts:
                if p.startswith("@"):
                    return p[1:]
            if parts:
                return parts[0].replace("@", "")
        return clean

    def scrape(self, target: str, limit: int = 25, **kwargs) -> List[ScrapedItem]:
        """
        Scrapes public videos from TikTok.
        Target formats:
        - '@khaby.lame' or 'khaby.lame'
        - 'tag:dance' or '#dance'
        """
        self.enforce_rate_limit()
        target = target.strip()
        items = []

        is_tag = target.startswith("tag:") or target.startswith("#")
        if is_tag:
            tag_name = target.replace("tag:", "").replace("#", "").strip()
            url = f"https://www.tiktok.com/tag/{tag_name}"
            target_name = f"#{tag_name}"
        else:
            username = self._extract_username(target)
            url = f"https://www.tiktok.com/@{username}"
            target_name = f"@{username}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.tiktok.com/",
        }

        res = self.session.request(url, method="GET", headers=headers)
        if res.get("status") != 200 or not res.get("content"):
            logger.warning("TikTok request failed with status: %s", res.get("status"))
            return []

        html = res["content"]

        # 1. Search for __UNIVERSAL_DATA_FOR_REHYDRATION__
        match = re.search(
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">({.*?})</script>',
            html,
        )
        # 2. Search for SIGI_STATE
        if not match:
            match = re.search(r'<script id="SIGI_STATE" type="application/json">({.*?})</script>', html)

        if match:
            try:
                data = json.loads(match.group(1))

                # Check ItemModule in SIGI_STATE
                item_module = data.get("ItemModule", {})
                if not item_module:
                    # Check default scope in universal data
                    default_scope = data.get("__DEFAULT_SCOPE__", {})
                    user_detail = default_scope.get("webapp.user-detail", {})
                    item_list = user_detail.get("itemList", [])
                    item_module = user_detail.get("itemModule", {})

                for vid_id, vid_info in list(item_module.items())[:limit]:
                    desc = vid_info.get("desc", "")
                    author = vid_info.get("author", target_name)
                    stats = vid_info.get("stats", {})
                    video_meta = vid_info.get("video", {})
                    create_time = vid_info.get("createTime", 0)

                    date_str = ""
                    if create_time:
                        try:
                            date_str = datetime.utcfromtimestamp(int(create_time)).isoformat() + "Z"
                        except Exception:
                            pass

                    media_urls = []
                    cover = video_meta.get("cover") or video_meta.get("dynamicCover")
                    if cover:
                        media_urls.append(cover)
                    play_addr = video_meta.get("playAddr") or video_meta.get("downloadAddr")
                    if play_addr:
                        media_urls.append(play_addr)

                    tags = [t.get("hashtagName") for t in vid_info.get("textExtra", []) if t.get("hashtagName")]

                    item = ScrapedItem(
                        id=str(vid_id),
                        platform="tiktok",
                        target=target_name,
                        author=f"@{author}",
                        title=desc[:60] if desc else f"TikTok by @{author}",
                        text=desc,
                        url=f"https://www.tiktok.com/@{author}/video/{vid_id}",
                        timestamp=date_str,
                        metrics={
                            "views": stats.get("playCount", 0),
                            "likes": stats.get("diggCount", 0),
                            "comments": stats.get("commentCount", 0),
                            "shares": stats.get("shareCount", 0),
                        },
                        media_urls=media_urls,
                        tags=tags,
                        extra={
                            "music": vid_info.get("music", {}).get("title", ""),
                            "duration": video_meta.get("duration", 0),
                        },
                    )
                    items.append(item)
            except Exception as e:
                logger.warning("Error parsing TikTok JSON state: %s", e)

        logger.info("Scraped %d TikTok items for target: %s", len(items), target)
        return items
