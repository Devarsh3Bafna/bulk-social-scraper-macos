"""
Platform Scraper Registry & Factory
"""

from typing import Dict, Type
from ..core.base import BaseScraper
from .reddit import RedditScraper
from .twitter import TwitterScraper
from .instagram import InstagramScraper
from .facebook import FacebookScraper
from .youtube import YouTubeScraper
from .tiktok import TikTokScraper
from .pinterest import PinterestScraper
from .linkedin import LinkedInScraper

SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    "instagram": InstagramScraper,
    "facebook": FacebookScraper,
    "fb": FacebookScraper,
    "ig": InstagramScraper,
    "reddit": RedditScraper,
    "twitter": TwitterScraper,
    "x": TwitterScraper,
    "youtube": YouTubeScraper,
    "tiktok": TikTokScraper,
    "pinterest": PinterestScraper,
    "linkedin": LinkedInScraper,
}


def get_scraper_for_platform(platform_name: str, session=None, delay: float = 1.5) -> BaseScraper:
    """Instantiates the scraper registered for platform_name."""
    key = platform_name.lower().strip()
    scraper_cls = SCRAPER_REGISTRY.get(key)
    if not scraper_cls:
        raise ValueError(
            f"Unsupported platform: '{platform_name}'. Supported: {list(SCRAPER_REGISTRY.keys())}"
        )
    return scraper_cls(session=session, delay=delay)


def detect_platform_from_url(url: str) -> str:
    """Detects social media platform from a URL."""
    lowered = url.lower()
    if "instagram.com" in lowered:
        return "instagram"
    if "facebook.com" in lowered or "fb.watch" in lowered:
        return "facebook"
    if "reddit.com" in lowered or "redd.it" in lowered:
        return "reddit"
    if "twitter.com" in lowered or "x.com" in lowered:
        return "twitter"
    if "youtube.com" in lowered or "youtu.be" in lowered:
        return "youtube"
    if "tiktok.com" in lowered:
        return "tiktok"
    if "pinterest.com" in lowered:
        return "pinterest"
    if "linkedin.com" in lowered:
        return "linkedin"
    return ""
