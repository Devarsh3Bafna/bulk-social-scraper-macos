"""
Lightweight Web Dashboard Server for macOS Bulk Social Media Scraper
Zero-dependency HTTP server using standard library with REST API for Safari & Chrome.
"""

import os
import sys
import json
import urllib.parse
import webbrowser
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import logging
from ..core.orchestrator import BulkOrchestrator
from ..core.macos_notifier import notifier
from ..platforms import SCRAPER_REGISTRY

logger = logging.getLogger("BulkScraper.Web")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
OUTPUT_DIR = "output"
DOWNLOADS_DIR = "downloads"


class ScraperHTTPHandler(SimpleHTTPRequestHandler):
    """Handles static files and scraper REST API endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # REST API endpoints
        if path == "/api/status":
            self._send_json({"status": "running", "version": "1.0.0", "platform": "macOS"})
            return

        elif path == "/api/platforms":
            self._send_json({"platforms": list(SCRAPER_REGISTRY.keys())})
            return

        elif path == "/api/files":
            files = []
            if os.path.exists(OUTPUT_DIR):
                for f in sorted(os.listdir(OUTPUT_DIR), reverse=True):
                    if not f.startswith("."):
                        fpath = os.path.join(OUTPUT_DIR, f)
                        files.append({
                            "name": f,
                            "size": os.path.getsize(fpath),
                            "modified": os.path.getmtime(fpath),
                            "path": f"/output/{f}",
                        })
            self._send_json({"files": files})
            return

        elif path.startswith("/output/"):
            # Serve files from output directory
            rel_file = path.replace("/output/", "").lstrip("/")
            full_path = os.path.join(OUTPUT_DIR, rel_file)
            if os.path.exists(full_path):
                self._serve_disk_file(full_path)
                return
            else:
                self.send_error(404, "File not found")
                return

        elif path.startswith("/downloads/"):
            # Serve files from downloads directory
            rel_file = path.replace("/downloads/", "").lstrip("/")
            full_path = os.path.join(DOWNLOADS_DIR, rel_file)
            if os.path.exists(full_path):
                self._serve_disk_file(full_path)
                return
            else:
                self.send_error(404, "Media file not found")
                return

        # Default to static files (index.html, style.css, app.js)
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body = json.loads(raw_body.decode("utf-8"))
        except Exception:
            body = {}

        if path == "/api/scrape":
            targets = body.get("targets", [])
            if not targets and body.get("target"):
                targets = [{
                    "platform": body.get("platform", "reddit"),
                    "target": body.get("target"),
                    "limit": int(body.get("limit", 20)),
                    "sort": body.get("sort", "hot"),
                }]

            if not targets:
                self._send_json({"error": "No targets provided"}, status=400)
                return

            download_media = body.get("download_media", False)
            orchestrator = BulkOrchestrator()
            summary = orchestrator.run_bulk(targets, download_media=download_media)

            # Convert ScrapedItem objects to dict for JSON serialization
            serialized_items = [it.to_dict() for it in summary.get("items", [])]
            summary_copy = dict(summary)
            summary_copy["items"] = serialized_items

            self._send_json({"success": True, "summary": summary_copy})
            return

        elif path == "/api/notify":
            title = body.get("title", "Bulk Scraper macOS")
            msg = body.get("message", "Web Dashboard test notification.")
            sound = body.get("sound", "Hero")
            ok = notifier.notify(title=title, message=msg, sound=sound)
            notifier.play_sound(sound)
            self._send_json({"success": ok})
            return

        elif path == "/api/scrape_posts":
            from ..extractor import scrape_post_url
            urls = body.get("urls", [])
            if not urls and body.get("url"):
                urls = [body.get("url")]

            start_t = datetime.now()
            items = [scrape_post_url(u) for u in urls if u and u.strip()]
            elapsed = round((datetime.now() - start_t).total_seconds(), 2)

            os.makedirs(OUTPUT_DIR, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = os.path.join(OUTPUT_DIR, f"real_engagements_{ts}.csv")
            with open(csv_file, "w", encoding="utf-8-sig") as f:
                f.write("Platform,Page Name,Page Link,Followers,Views,Likes,Comments,Date Posted,Original Link,Status,Last Checked\n")
                for it in items:
                    f.write(f'"{it.get("platform","").capitalize()}","{it.get("page_name","")}","{it.get("page_link","")}","{it.get("followers","")}","{it.get("views","")}","{it.get("likes","")}","{it.get("comments","")}","{it.get("posted_date","")}","{it.get("original_url","")}","{it.get("status","")}","{it.get("last_checked","")}"\n')

            self._send_json({
                "success": True,
                "total": len(items),
                "elapsed_seconds": elapsed,
                "last_updated": datetime.now().strftime("%b %d, %Y %I:%M:%S %p"),
                "items": items,
                "csv_download": f"/output/{os.path.basename(csv_file)}"
            })
            return

        self.send_error(404, "Endpoint not found")

    def _serve_disk_file(self, full_path: str):
        content_type = "application/octet-stream"
        if full_path.endswith(".csv"):
            content_type = "text/csv; charset=utf-8"
        elif full_path.endswith(".json"):
            content_type = "application/json; charset=utf-8"
        elif full_path.endswith(".html"):
            content_type = "text/html; charset=utf-8"
        elif full_path.endswith((".jpg", ".jpeg")):
            content_type = "image/jpeg"
        elif full_path.endswith(".png"):
            content_type = "image/png"
        elif full_path.endswith(".mp4"):
            content_type = "video/mp4"

        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")


def launch_web_server(port: int = 8501, auto_open: bool = True):
    """Starts the Web Dashboard server and opens it in Safari/Chrome."""
    server_address = ("", port)
    try:
        httpd = HTTPServer(server_address, ScraperHTTPHandler)
    except OSError:
        # Fallback to alternate port if 8501 is taken
        port = 8502
        server_address = ("", port)
        httpd = HTTPServer(server_address, ScraperHTTPHandler)

    url = f"http://localhost:{port}"
    print(f"\n🍎 macOS Bulk Scraper Web Dashboard running at: {url}")
    print(f"Press Control+C in Terminal to stop the server.\n")

    if auto_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Web Dashboard server...")
        httpd.server_close()
