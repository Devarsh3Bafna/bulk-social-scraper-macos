"""
LinkedIn Public Post Scraper for macOS Bulk Scraper
Scrapes public organization posts and open activity streams.
"""

from typing import List
import re
import urllib.parse
import logging
from ..core.base import BaseScraper, ScrapedItem

logger = logging.getLogger("BulkScraper.LinkedIn")


class LinkedInScraper(BaseScraper):
    platform_name = "linkedin"

    def scrape(self, target: str, limit: int = 25, **kwargs) -> List[ScrapedItem]:
        """
        Scrapes public posts from LinkedIn companies or public post URLs.
        Target formats:
        - 'company:google' or 'google'
        - 'https://www.linkedin.com/company/apple/posts/'
        """
        target = target.strip()
        cleaned = self.clean_target(target)
        self.enforce_rate_limit()

        if target.startswith("http://") or target.startswith("https://"):
            url = target
        elif cleaned.startswith("company:"):
            comp = cleaned.replace("company:", "").strip()
            url = f"https://www.linkedin.com/company/{comp}/posts/"
        else:
            url = f"https://www.linkedin.com/company/{cleaned}/posts/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        res = self.session.request(url, method="GET", headers=headers)
        if res.get("status") != 200 or not res.get("content"):
            logger.warning("LinkedIn request failed with status: %s", res.get("status"))
            return []

        html = res["content"]
        items = []

        # Find post elements in public company feed
        post_blocks = re.findall(
            r'data-activity-id="urn:li:activity:(\d+)".*?<p class="[^"]*break-words[^"]*">(.*?)</p>',
            html,
            re.DOTALL,
        )

        for act_id, p_text in post_blocks[:limit]:
            clean_text = re.sub(r"<[^>]+>", "", p_text).strip()
            items.append(
                ScrapedItem(
                    id=str(act_id),
                    platform="linkedin",
                    target=cleaned,
                    author=cleaned,
                    title=f"LinkedIn update from {cleaned}",
                    text=clean_text,
                    url=f"https://www.linkedin.com/feed/update/urn:li:activity:{act_id}/",
                    metrics={},
                )
            )

        logger.info("Scraped %d LinkedIn items for target: %s", len(items), target)
        return items
