"""
Twitter / X Scraper for macOS Bulk Scraper
Scrapes public tweets, user timelines, and media via syndication endpoints and web mirrors.
"""

from typing import List
import json
import re
import urllib.parse
from datetime import datetime
import logging
from ..core.base import BaseScraper, ScrapedItem

logger = logging.getLogger("BulkScraper.Twitter")


class TwitterScraper(BaseScraper):
    platform_name = "twitter"

    def _extract_username(self, target: str) -> str:
        clean = self.clean_target(target)
        if "twitter.com/" in clean or "x.com/" in clean:
            parsed = urllib.parse.urlparse(clean if "://" in clean else f"https://{clean}")
            parts = parsed.path.strip("/").split("/")
            if parts:
                return parts[0]
        return clean

    def scrape(self, target: str, limit: int = 25, **kwargs) -> List[ScrapedItem]:
        """
        Scrapes tweets from Twitter/X.
        Target formats:
        - '@elonmusk' or 'elonmusk'
        - 'https://twitter.com/user'
        - 'https://x.com/user'
        """
        username = self._extract_username(target)
        self.enforce_rate_limit()

        # Try Twitter syndication widget timeline endpoint
        endpoint = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://platform.twitter.com/",
        }

        res = self.session.request(endpoint, method="GET", headers=headers)
        items = []

        if res.get("status") == 200 and res.get("content"):
            content = res["content"]
            # Look for JSON state script: __NEXT_DATA__
            match = re.search(r'<script id="__NEXT_DATA__" type="application/json">({.*?})</script>', content)
            if match:
                try:
                    next_data = json.loads(match.group(1))
                    entries = (
                        next_data.get("props", {})
                        .get("pageProps", {})
                        .get("timeline", {})
                        .get("entries", [])
                    )

                    for entry in entries[:limit]:
                        tweet_content = entry.get("content", {}).get("tweet", {})
                        if not tweet_content:
                            continue

                        tweet_id = tweet_content.get("id_str") or str(tweet_content.get("id", ""))
                        text = tweet_content.get("full_text") or tweet_content.get("text", "")
                        user = tweet_content.get("user", {})
                        author = user.get("screen_name", username)
                        user_name = user.get("name", "")
                        created_at = tweet_content.get("created_at", "")

                        likes = tweet_content.get("favorite_count", 0)
                        retweets = tweet_content.get("retweet_count", 0)
                        replies = tweet_content.get("reply_count", 0)

                        media_urls = []
                        entities = tweet_content.get("extended_entities", {}) or tweet_content.get(
                            "entities", {}
                        )
                        for media in entities.get("media", []):
                            media_url = media.get("media_url_https")
                            if media_url:
                                media_urls.append(media_url)
                            # Video variants
                            video_info = media.get("video_info", {})
                            variants = video_info.get("variants", [])
                            for v in sorted(variants, key=lambda x: x.get("bitrate", 0), reverse=True):
                                if v.get("content_type") == "video/mp4" and v.get("url"):
                                    media_urls.append(v["url"])
                                    break

                        # Extract hashtags
                        hashtags = [
                            ht.get("text") for ht in tweet_content.get("entities", {}).get("hashtags", [])
                        ]

                        item = ScrapedItem(
                            id=tweet_id,
                            platform="twitter",
                            target=username,
                            author=f"@{author}",
                            title=f"Tweet by {user_name or author}",
                            text=text,
                            url=f"https://x.com/{author}/status/{tweet_id}",
                            timestamp=created_at,
                            metrics={
                                "likes": likes,
                                "retweets": retweets,
                                "replies": replies,
                            },
                            media_urls=media_urls,
                            tags=hashtags,
                            extra={
                                "user_followers": user.get("followers_count", 0),
                                "verified": user.get("verified", False),
                            },
                        )
                        items.append(item)
                except Exception as e:
                    logger.warning("Error parsing Twitter NextData: %s", e)

        # Fallback to CDN Syndication profile API if __NEXT_DATA__ yielded nothing
        if not items:
            cdn_url = f"https://cdn.syndication.twimg.com/widgets/timeline/profile?screen_name={username}"
            res_cdn = self.session.request(cdn_url, method="GET", is_json=True)
            if res_cdn.get("status") == 200 and res_cdn.get("json"):
                cdn_data = res_cdn["json"]
                # Timeline widget HTML or json entries
                body_html = cdn_data.get("body", "")
                if body_html:
                    # Regex extraction of tweets from widget HTML
                    tweet_blocks = re.findall(
                        r'data-tweet-id="(\d+)".*?<p class="timeline-Tweet-text"[^>]*>(.*?)</p>',
                        body_html,
                        re.DOTALL,
                    )
                    for t_id, t_text in tweet_blocks[:limit]:
                        clean_text = re.sub(r"<[^>]+>", "", t_text).strip()
                        items.append(
                            ScrapedItem(
                                id=t_id,
                                platform="twitter",
                                target=username,
                                author=f"@{username}",
                                text=clean_text,
                                url=f"https://x.com/{username}/status/{t_id}",
                                metrics={},
                            )
                        )

        logger.info("Scraped %d tweets for Twitter target: %s", len(items), username)
        return items
