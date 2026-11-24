"""
YouTube Scraper for macOS Bulk Scraper
Scrapes public video metadata, channel videos, shorts, and search queries using ytInitialData JSON extraction.
Zero API keys needed.
"""

from typing import List
import json
import re
import urllib.parse
import logging
from ..core.base import BaseScraper, ScrapedItem

logger = logging.getLogger("BulkScraper.YouTube")


class YouTubeScraper(BaseScraper):
    platform_name = "youtube"

    def scrape(self, target: str, limit: int = 25, **kwargs) -> List[ScrapedItem]:
        """
        Scrapes videos from YouTube.
        Target formats:
        - 'apple' or '@apple' -> Channel
        - 'search:artificial intelligence' -> Search query
        - 'https://www.youtube.com/@mkbhd/videos'
        """
        target = target.strip()
        cleaned = self.clean_target(target)
        self.enforce_rate_limit()

        if target.startswith("search:") or target.startswith("query:"):
            query = target.split(":", 1)[1].strip()
            encoded_q = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded_q}"
        elif "youtube.com/" in target or "youtu.be/" in target:
            url = target
        elif cleaned.startswith("@"):
            url = f"https://www.youtube.com/{cleaned}/videos"
        else:
            url = f"https://www.youtube.com/@{cleaned}/videos"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        res = self.session.request(url, method="GET", headers=headers)
        if res.get("status") != 200 or not res.get("content"):
            logger.warning("YouTube request failed with status: %s", res.get("status"))
            return []

        html = res["content"]
        items = []

        # Find ytInitialData script
        match = re.search(r"var ytInitialData\s*=\s*({.*?});</script>", html)
        if not match:
            match = re.search(r"ytInitialData\s*=\s*({.*?});", html)

        if not match:
            logger.warning("Could not find ytInitialData on page")
            return []

        try:
            data = json.loads(match.group(1))
            # Extract video renderers recursively
            renderers = []

            def find_renderers(obj):
                if isinstance(obj, dict):
                    if "videoRenderer" in obj:
                        renderers.append(obj["videoRenderer"])
                    elif "richItemRenderer" in obj:
                        item_content = obj["richItemRenderer"].get("content", {})
                        if "videoRenderer" in item_content:
                            renderers.append(item_content["videoRenderer"])
                        elif "shortsLockupViewModel" in item_content:
                            renderers.append(item_content["shortsLockupViewModel"])
                    else:
                        for v in obj.values():
                            find_renderers(v)
                elif isinstance(obj, list):
                    for elem in obj:
                        find_renderers(elem)

            find_renderers(data)

            for rend in renderers[:limit]:
                # Standard video renderer
                if "videoId" in rend:
                    video_id = rend.get("videoId", "")
                    title_obj = rend.get("title", {})
                    title = ""
                    if "runs" in title_obj and title_obj["runs"]:
                        title = title_obj["runs"][0].get("text", "")
                    elif "simpleText" in title_obj:
                        title = title_obj["simpleText"]

                    channel_title = ""
                    owner_obj = rend.get("ownerText", {}) or rend.get("shortBylineText", {})
                    if "runs" in owner_obj and owner_obj["runs"]:
                        channel_title = owner_obj["runs"][0].get("text", "")

                    views_text = rend.get("viewCountText", {}).get("simpleText", "")
                    views = 0
                    if views_text:
                        digits = re.sub(r"[^\d]", "", views_text)
                        views = int(digits) if digits else 0

                    duration = rend.get("lengthText", {}).get("simpleText", "")
                    published = rend.get("publishedTimeText", {}).get("simpleText", "")

                    desc = ""
                    desc_snippets = rend.get("detailedMetadataSnippets", [])
                    if desc_snippets:
                        snippet_text = desc_snippets[0].get("snippetText", {})
                        desc = "".join(r.get("text", "") for r in snippet_text.get("runs", []))

                    thumbs = rend.get("thumbnail", {}).get("thumbnails", [])
                    thumb_url = thumbs[-1].get("url") if thumbs else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

                    item = ScrapedItem(
                        id=video_id,
                        platform="youtube",
                        target=cleaned,
                        author=channel_title,
                        title=title,
                        text=desc,
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        timestamp=published,
                        metrics={"views": views, "duration": duration},
                        media_urls=[thumb_url] if thumb_url else [],
                        extra={"video_id": video_id, "duration": duration},
                    )
                    items.append(item)

                # Shorts Lockup View Model
                elif "entityId" in rend:
                    entity_id = rend.get("entityId", "")
                    item = ScrapedItem(
                        id=entity_id,
                        platform="youtube",
                        target=cleaned,
                        title="YouTube Short",
                        url=f"https://www.youtube.com/shorts/{entity_id}",
                        metrics={},
                    )
                    items.append(item)

        except Exception as e:
            logger.warning("Error parsing YouTube data: %s", e)

        logger.info("Scraped %d videos from YouTube for target: %s", len(items), target)
        return items
