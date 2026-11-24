"""
Reddit Scraper for macOS Bulk Scraper
Scrapes subreddits (hot, new, top), user submissions, and search queries via Reddit JSON endpoints.
No API keys required.
"""

from typing import List
import urllib.parse
from datetime import datetime
import logging
from ..core.base import BaseScraper, ScrapedItem

logger = logging.getLogger("BulkScraper.Reddit")


class RedditScraper(BaseScraper):
    platform_name = "reddit"

    def scrape(self, target: str, limit: int = 25, sort: str = "hot", **kwargs) -> List[ScrapedItem]:
        """
        Scrapes submissions from Reddit.
        Target formats:
        - 'technology' or 'r/technology' -> Subreddit
        - 'u/spez' or 'user:spez' -> User submissions
        - 'query:artificial intelligence' or 'search:ai' -> Search query
        - full reddit URL -> Subreddit or post
        """
        target = target.strip()
        cleaned = self.clean_target(target)
        endpoint = ""

        if target.startswith("http://") or target.startswith("https://"):
            parsed = urllib.parse.urlparse(target)
            path = parsed.path.rstrip("/")
            endpoint = f"https://www.reddit.com{path}.json"
        elif target.startswith("u/") or target.startswith("user:"):
            user = target.split(":")[-1].replace("u/", "").strip()
            endpoint = f"https://www.reddit.com/user/{user}/submitted.json"
        elif target.startswith("query:") or target.startswith("search:"):
            query = target.split(":", 1)[1].strip()
            params = urllib.parse.urlencode({"q": query, "limit": min(limit, 100), "sort": "relevance"})
            endpoint = f"https://www.reddit.com/search.json?{params}"
        else:
            # Default to subreddit
            endpoint = f"https://www.reddit.com/r/{cleaned}/{sort}.json"

        # Reddit requires a descriptive custom User-Agent to avoid 429
        headers = {
            "User-Agent": "macOS:bulk-social-scraper:v1.0 (by /u/mac_researcher)",
            "Accept": "application/json",
        }

        self.enforce_rate_limit()

        params = {"limit": min(limit, 100), "raw_json": 1}
        logger.info("Fetching Reddit posts from: %s", endpoint)
        res = self.session.request(endpoint, method="GET", headers=headers, params=params, is_json=True)

        if res.get("status") != 200 or not res.get("json"):
            logger.warning("Reddit request failed with status: %s", res.get("status"))
            return []

        data = res["json"]
        items = []

        # Handle post list listing
        children = []
        if isinstance(data, dict):
            children = data.get("data", {}).get("children", [])
        elif isinstance(data, list) and data:
            # In case of post comment thread
            children = data[0].get("data", {}).get("children", [])

        for child in children[:limit]:
            post = child.get("data", {})
            if not post:
                continue

            post_id = post.get("id", "")
            title = post.get("title", "")
            selftext = post.get("selftext", "")
            author = post.get("author", "")
            subreddit = post.get("subreddit", cleaned)
            score = post.get("score", 0)
            num_comments = post.get("num_comments", 0)
            upvote_ratio = post.get("upvote_ratio", 1.0)
            created_utc = post.get("created_utc", 0)
            permalink = f"https://www.reddit.com{post.get('permalink', '')}"

            date_str = ""
            if created_utc:
                try:
                    date_str = datetime.utcfromtimestamp(created_utc).isoformat() + "Z"
                except Exception:
                    pass

            # Extract media attachments
            media_urls = []
            url = post.get("url", "")
            post_hint = post.get("post_hint", "")

            if post_hint == "image" or any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                media_urls.append(url)
            elif "gallery_data" in post:
                items_gallery = post.get("gallery_data", {}).get("items", [])
                for gi in items_gallery:
                    media_id = gi.get("media_id")
                    if media_id:
                        media_urls.append(f"https://i.redd.it/{media_id}.jpg")
            elif "reddit_video" in post.get("media", {}):
                video_url = post["media"]["reddit_video"].get("fallback_url")
                if video_url:
                    media_urls.append(video_url)

            # Preview images fallback
            if not media_urls and "preview" in post:
                images = post["preview"].get("images", [])
                for img in images:
                    source_url = img.get("source", {}).get("url")
                    if source_url:
                        media_urls.append(source_url.replace("&amp;", "&"))

            tags = []
            flair = post.get("link_flair_text")
            if flair:
                tags.append(flair)
            if post.get("over_18"):
                tags.append("NSFW")
            if post.get("spoiler"):
                tags.append("Spoiler")

            scraped_item = ScrapedItem(
                id=post_id,
                platform="reddit",
                target=subreddit,
                author=f"u/{author}" if author else "",
                title=title,
                text=selftext,
                url=permalink,
                timestamp=date_str,
                metrics={
                    "upvotes": score,
                    "comments": num_comments,
                    "upvote_ratio": upvote_ratio,
                },
                media_urls=media_urls,
                tags=tags,
                extra={
                    "subreddit": subreddit,
                    "is_video": post.get("is_video", False),
                    "is_self": post.get("is_self", True),
                },
            )
            items.append(scraped_item)

        logger.info("Successfully scraped %d items from Reddit: %s", len(items), target)
        return items
