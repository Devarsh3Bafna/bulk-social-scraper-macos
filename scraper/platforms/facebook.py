"""
Original Facebook Scraper for macOS Bulk Scraper
Scrapes public Facebook posts, reels, and video links using Headless Chrome engine.
Extracts Page Name, Page Link, Followers, Likes, Comments, Views, and Posted Date.
No login required.
"""

from typing import List, Dict, Any
from ..core.base import BaseScraper, ScrapedItem
from ..extractor import parse_facebook_url


class FacebookScraper(BaseScraper):
    platform_name = "facebook"

    def scrape_post_by_url(self, post_url: str) -> Dict[str, Any]:
        """Scrapes live Facebook post/reel data without login."""
        return parse_facebook_url(post_url)

    def scrape(self, target: str, limit: int = 25, **kwargs) -> List[ScrapedItem]:
        target = target.strip()
        res_meta = self.scrape_post_by_url(target)
        item = ScrapedItem(
            id=res_meta.get("page_name") or "fb_post",
            platform="facebook",
            target=res_meta.get("page_name", "—"),
            author=res_meta.get("page_name", "—"),
            title=f"Facebook post by {res_meta.get('page_name', '—')}",
            text=res_meta.get("caption", "—"),
            url=res_meta.get("original_url", target),
            timestamp=res_meta.get("posted_date", "—"),
            metrics={
                "likes": res_meta.get("likes", "—"),
                "comments": res_meta.get("comments", "—"),
                "views": res_meta.get("views", "—"),
                "followers": res_meta.get("followers", "—"),
            },
            extra={"status": res_meta.get("status", "Live Verified")},
        )
        return [item]
