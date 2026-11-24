"""
Base Scraper Class & Standardized Data Model
Defines the unified schema across all social media platforms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional
import time
import logging

logger = logging.getLogger("BulkScraper.Base")


@dataclass
class ScrapedItem:
    """Standardized representation of a scraped social media post or entry."""

    id: str
    platform: str
    target: str
    author: str = ""
    title: str = ""
    text: str = ""
    url: str = ""
    timestamp: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    media_urls: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_flat_dict(self) -> Dict[str, Any]:
        """Flattens metrics, tags, and media_urls for easy CSV export."""
        d = asdict(self)
        d["media_urls"] = "; ".join(self.media_urls)
        d["tags"] = ", ".join(self.tags)
        # Flatten metrics
        metrics = d.pop("metrics", {})
        for k, v in metrics.items():
            d[f"metric_{k}"] = v
        d.pop("extra", None)
        return d


class BaseScraper(ABC):
    """Abstract base class for all platform scrapers."""

    platform_name: str = "generic"

    def __init__(self, session=None, delay: float = 1.5):
        from .session import ResilientSession

        self.session = session or ResilientSession()
        self.delay = delay
        self.last_request_time = 0.0
        self.items_scraped = 0
        self.error_count = 0

    def enforce_rate_limit(self):
        """Enforces minimum inter-request delay to prevent blocking."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()

    def clean_target(self, target: str) -> str:
        """Strips leading '@', 'r/', 'u/', trailing slashes, etc."""
        target = target.strip()
        if target.startswith("@"):
            target = target[1:]
        elif target.startswith("r/") or target.startswith("u/"):
            target = target[2:]
        return target.rstrip("/")

    @abstractmethod
    def scrape(self, target: str, limit: int = 25, **kwargs) -> List[ScrapedItem]:
        """
        Scrapes posts, submissions, or media from target.
        Target can be a username, hashtag, subreddit, search query, or URL.
        """
        pass

    def test_connection(self) -> bool:
        """Verifies if the scraper can reach platform services."""
        return True
