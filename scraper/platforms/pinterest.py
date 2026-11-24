"""
Pinterest Scraper for macOS Bulk Scraper
Scrapes public boards, pins, image assets, and descriptions.
"""

from typing import List
import json
import re
import urllib.parse
import logging
from ..core.base import BaseScraper, ScrapedItem

logger = logging.getLogger("BulkScraper.Pinterest")


class PinterestScraper(BaseScraper):
    platform_name = "pinterest"

    def scrape(self, target: str, limit: int = 25, **kwargs) -> List[ScrapedItem]:
        """
        Scrapes pins from Pinterest.
        Target formats:
        - 'archdigest' or '@archdigest' -> User profile
        - 'search:interior design' -> Search query
        - 'https://pinterest.com/username/boardname/'
        """
        target = target.strip()
        cleaned = self.clean_target(target)
        self.enforce_rate_limit()

        if target.startswith("search:") or target.startswith("query:"):
            q = target.split(":", 1)[1].strip()
            url = f"https://www.pinterest.com/search/pins/?q={urllib.parse.quote(q)}"
        elif "pinterest.com/" in target:
            url = target
        else:
            url = f"https://www.pinterest.com/{cleaned}/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        res = self.session.request(url, method="GET", headers=headers)
        if res.get("status") != 200 or not res.get("content"):
            logger.warning("Pinterest request failed with status: %s", res.get("status"))
            return []

        html = res["content"]
        items = []

        # Pinterest embeds data in script tag: __PWS_DATA__
        match = re.search(r'<script id="__PWS_DATA__" type="application/json">({.*?})</script>', html)
        if match:
            try:
                data = json.loads(match.group(1))
                props = data.get("props", {})
                initial_state = props.get("initialState", {})
                pins_dict = initial_state.get("pins", {})

                for pin_id, pin_info in list(pins_dict.items())[:limit]:
                    desc = pin_info.get("description") or pin_info.get("grid_title") or ""
                    title = pin_info.get("title") or pin_info.get("grid_title") or ""
                    pinner = pin_info.get("pinner", {}).get("username", cleaned)
                    images = pin_info.get("images", {})

                    media_urls = []
                    # Try original or highest resolution
                    orig_img = images.get("orig", {}).get("url") or images.get("736x", {}).get("url")
                    if orig_img:
                        media_urls.append(orig_img)

                    item = ScrapedItem(
                        id=str(pin_id),
                        platform="pinterest",
                        target=cleaned,
                        author=f"@{pinner}",
                        title=title,
                        text=desc,
                        url=f"https://www.pinterest.com/pin/{pin_id}/",
                        metrics={
                            "repins": pin_info.get("repin_count", 0),
                            "comments": pin_info.get("comment_count", 0),
                        },
                        media_urls=media_urls,
                    )
                    items.append(item)
            except Exception as e:
                logger.warning("Error parsing Pinterest JSON: %s", e)

        # Fallback regex extraction of pin links & images
        if not items:
            pin_matches = re.findall(
                r'href="/pin/(\d+)/".*?src="([^"]+pinimg\.com/[^"]+)"', html, re.DOTALL
            )
            for p_id, p_img in pin_matches[:limit]:
                # Upgrade thumbnail to higher quality
                high_res_img = p_img.replace("/236x/", "/736x/").replace("/474x/", "/736x/")
                items.append(
                    ScrapedItem(
                        id=str(p_id),
                        platform="pinterest",
                        target=cleaned,
                        author=cleaned,
                        url=f"https://www.pinterest.com/pin/{p_id}/",
                        media_urls=[high_res_img],
                    )
                )

        logger.info("Scraped %d Pinterest pins for target: %s", len(items), target)
        return items
