"""
Resilient HTTP Client for macOS Bulk Social Media Scraper
Features automatic User-Agent rotation (macOS Safari & Chrome),
exponential backoff retry, proxy support, and JSON parsing.
Includes fallback to standard library urllib to guarantee zero initial dependency friction.
"""

import os
import json
import random
import time
import urllib.request
import urllib.error
import urllib.parse
import ssl
import gzip
import io
import logging

logger = logging.getLogger("BulkScraper.Session")

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 15_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:130.0) Gecko/20100101 Firefox/130.0",
]


class ResilientSession:
    """Manages HTTP requests with retries, headers, proxies, and error handling."""

    def __init__(
        self,
        user_agents_file: str = None,
        proxies: list = None,
        timeout: float = 20.0,
        max_retries: int = 3,
        base_delay: float = 1.5,
    ):
        self.proxies = proxies or []
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.user_agents = self._load_user_agents(user_agents_file)
        self.ssl_context = ssl.create_default_context()
        # In case system certs have issues on some local macOS setups
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def _load_user_agents(self, filepath: str = None) -> list:
        if filepath and os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    agents = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                if agents:
                    return agents
            except Exception:
                pass
        return DEFAULT_USER_AGENTS

    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)

    def get_default_headers(self, custom_headers: dict = None) -> dict:
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def request(
        self,
        url: str,
        method: str = "GET",
        headers: dict = None,
        data: bytes = None,
        params: dict = None,
        is_json: bool = False,
    ) -> dict:
        """
        Executes an HTTP request with exponential backoff on errors and returns a dict with:
        {'status': int, 'content': str, 'json': dict/list or None, 'headers': dict}
        """
        if params:
            query_string = urllib.parse.urlencode(params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{query_string}"

        req_headers = self.get_default_headers(headers)
        if is_json:
            req_headers["Accept"] = "application/json, text/plain, */*"

        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers=req_headers,
                    method=method.upper(),
                )

                handlers = [urllib.request.HTTPSHandler(context=self.ssl_context)]
                if self.proxies:
                    proxy = random.choice(self.proxies)
                    handlers.append(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))

                opener = urllib.request.build_opener(*handlers)

                with opener.open(req, timeout=self.timeout) as response:
                    raw_content = response.read()
                    status_code = response.getcode()
                    resp_headers = dict(response.info())

                    # Handle gzip decompression
                    if resp_headers.get("Content-Encoding") == "gzip" or (
                        len(raw_content) >= 2 and raw_content[:2] == b"\x1f\x8b"
                    ):
                        try:
                            raw_content = gzip.GzipFile(fileobj=io.BytesIO(raw_content)).read()
                        except Exception:
                            pass

                    # Decode text
                    encoding = "utf-8"
                    content_type = resp_headers.get("Content-Type", "")
                    if "charset=" in content_type:
                        encoding = content_type.split("charset=")[-1].split(";")[0].strip()

                    try:
                        text_content = raw_content.decode(encoding, errors="replace")
                    except Exception:
                        text_content = raw_content.decode("utf-8", errors="replace")

                    json_data = None
                    if "application/json" in content_type or text_content.strip().startswith(("{", "[")):
                        try:
                            json_data = json.loads(text_content)
                        except Exception:
                            json_data = None

                    return {
                        "status": status_code,
                        "content": text_content,
                        "raw_bytes": raw_content,
                        "json": json_data,
                        "headers": resp_headers,
                        "url": url,
                    }

            except urllib.error.HTTPError as e:
                last_error = e
                status = e.code
                logger.warning(
                    "HTTP %d for URL %s (attempt %d/%d)",
                    status,
                    url,
                    attempt + 1,
                    self.max_retries + 1,
                )

                if status in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    backoff = (2**attempt) * self.base_delay + random.uniform(0.5, 1.5)
                    logger.info("Backing off for %.2fs due to HTTP %d", backoff, status)
                    time.sleep(backoff)
                    # Rotate user agent for next attempt
                    req_headers["User-Agent"] = self.get_random_user_agent()
                    continue
                else:
                    return {
                        "status": status,
                        "content": "",
                        "raw_bytes": b"",
                        "json": None,
                        "headers": {},
                        "error": str(e),
                        "url": url,
                    }

            except Exception as e:
                last_error = e
                logger.warning(
                    "Network error: %s for %s (attempt %d/%d)",
                    e,
                    url,
                    attempt + 1,
                    self.max_retries + 1,
                )
                if attempt < self.max_retries:
                    backoff = (2**attempt) * self.base_delay + random.uniform(0.5, 1.0)
                    time.sleep(backoff)
                    continue

        return {
            "status": 0,
            "content": "",
            "raw_bytes": b"",
            "json": None,
            "headers": {},
            "error": str(last_error),
            "url": url,
        }

    def get_json(self, url: str, headers: dict = None, params: dict = None) -> dict:
        """Helper to directly fetch and parse JSON."""
        res = self.request(url, method="GET", headers=headers, params=params, is_json=True)
        return res.get("json")
