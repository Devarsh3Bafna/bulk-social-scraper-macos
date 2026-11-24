"""
Data Exporter for macOS Bulk Social Media Scraper
Exports scraped data to CSV, JSON, JSONL, SQLite, and an elegant Apple-style HTML report.
"""

import os
import csv
import json
import sqlite3
from typing import List, Dict, Any
from datetime import datetime
import logging
from .base import ScrapedItem

logger = logging.getLogger("BulkScraper.Exporter")


class DataExporter:
    """Handles multi-format export of scraped social media data."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _generate_filename(self, prefix: str, ext: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prefix = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in prefix)
        return os.path.join(self.output_dir, f"{safe_prefix}_{timestamp}.{ext}")

    def export_csv(self, items: List[ScrapedItem], filename: str = None, prefix: str = "export") -> str:
        """Exports items to CSV with UTF-8-SIG for seamless opening in Apple Numbers and Microsoft Excel."""
        if not items:
            return ""

        filepath = filename or self._generate_filename(prefix, "csv")
        flat_records = [item.to_flat_dict() for item in items]

        # Gather all unique field names
        fieldnames = []
        for r in flat_records:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            writer.writerows(flat_records)

        logger.info("Exported %d items to CSV: %s", len(items), filepath)
        return filepath

    def export_json(
        self, items: List[ScrapedItem], filename: str = None, prefix: str = "export", jsonl: bool = False
    ) -> str:
        """Exports items to JSON or JSON Lines."""
        if not items:
            return ""

        ext = "jsonl" if jsonl else "json"
        filepath = filename or self._generate_filename(prefix, ext)

        records = [item.to_dict() for item in items]

        with open(filepath, "w", encoding="utf-8") as f:
            if jsonl:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            else:
                json.dump(records, f, indent=2, ensure_ascii=False)

        logger.info("Exported %d items to %s: %s", len(items), ext.upper(), filepath)
        return filepath

    def export_sqlite(self, items: List[ScrapedItem], db_path: str = None) -> str:
        """Stores scraped records in an SQLite database with indexing and deduplication."""
        if not items:
            return ""

        filepath = db_path or os.path.join(self.output_dir, "social_media_scrapes.db")
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scraped_posts (
                id TEXT NOT NULL,
                platform TEXT NOT NULL,
                target TEXT NOT NULL,
                author TEXT,
                title TEXT,
                text TEXT,
                url TEXT,
                timestamp TEXT,
                metrics_json TEXT,
                media_urls_json TEXT,
                tags_json TEXT,
                scraped_at TEXT,
                PRIMARY KEY (platform, id)
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_platform_target ON scraped_posts (platform, target);
            """
        )

        for item in items:
            cursor.execute(
                """
                INSERT OR REPLACE INTO scraped_posts 
                (id, platform, target, author, title, text, url, timestamp, metrics_json, media_urls_json, tags_json, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.platform,
                    item.target,
                    item.author,
                    item.title,
                    item.text,
                    item.url,
                    item.timestamp,
                    json.dumps(item.metrics, ensure_ascii=False),
                    json.dumps(item.media_urls, ensure_ascii=False),
                    json.dumps(item.tags, ensure_ascii=False),
                    item.scraped_at,
                ),
            )

        conn.commit()
        conn.close()
        logger.info("Exported %d items to SQLite: %s", len(items), filepath)
        return filepath

    def export_html_report(self, items: List[ScrapedItem], filename: str = None, prefix: str = "report") -> str:
        """
        Generates a standalone, interactive HTML report with Apple macOS aesthetic.
        Can be opened directly in Safari or Chrome.
        """
        if not items:
            return ""

        filepath = filename or self._generate_filename(prefix, "html")

        # Basic statistics
        platforms = {}
        total_media = 0
        for item in items:
            platforms[item.platform] = platforms.get(item.platform, 0) + 1
            total_media += len(item.media_urls)

        rows_html = []
        for i, it in enumerate(items):
            metrics_tags = "".join(
                f'<span class="badge metric">{k}: {v}</span>' for k, v in it.metrics.items()
            )
            media_thumbnails = "".join(
                f'<a href="{m}" target="_blank"><img src="{m}" class="thumb" onerror="this.style.display=\'none\'" /></a>'
                for m in it.media_urls[:4]
            )
            tags_html = "".join(f'<span class="tag">#{t}</span>' for t in it.tags)
            post_link = f'<a href="{it.url}" target="_blank" class="post-link">View Original &rarr;</a>' if it.url else ""

            row = f"""
            <tr class="item-row" data-platform="{it.platform}">
                <td><span class="badge platform platform-{it.platform}">{it.platform.upper()}</span></td>
                <td><strong>{it.author or it.target}</strong></td>
                <td>
                    {f'<div class="post-title">{it.title}</div>' if it.title else ''}
                    <div class="post-text">{it.text[:280] + ('...' if len(it.text) > 280 else '')}</div>
                    <div class="tags-container">{tags_html}</div>
                    <div class="media-container">{media_thumbnails}</div>
                    <div class="action-links">{post_link}</div>
                </td>
                <td><div class="metrics-container">{metrics_tags}</div></td>
                <td class="date-col">{it.timestamp or it.scraped_at[:10]}</td>
            </tr>
            """
            rows_html.append(row)

        platform_summary = "".join(
            f'<div class="stat-card"><span class="stat-num">{count}</span><span class="stat-label">{plat.title()}</span></div>'
            for plat, count in platforms.items()
        )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bulk Scraper - macOS Scrape Report</title>
    <style>
        :root {{
            --bg: #f5f5f7;
            --card-bg: rgba(255, 255, 255, 0.85);
            --text-main: #1d1d1f;
            --text-sub: #86868b;
            --border: #d2d2d7;
            --accent: #0071e3;
            --radius: 14px;
        }}
        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg: #000000;
                --card-bg: rgba(28, 28, 30, 0.85);
                --text-main: #f5f5f7;
                --text-sub: #a1a1a6;
                --border: #38383a;
                --accent: #2997ff;
            }}
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif; }}
        body {{ background-color: var(--bg); color: var(--text-main); padding: 40px 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 28px; font-weight: 700; letter-spacing: -0.5px; }}
        .header .subtitle {{ font-size: 14px; color: var(--text-sub); margin-top: 4px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; margin-bottom: 30px; }}
        .stat-card {{ background: var(--card-bg); backdrop-filter: blur(20px); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; text-align: center; }}
        .stat-num {{ font-size: 26px; font-weight: 700; color: var(--accent); display: block; }}
        .stat-label {{ font-size: 13px; color: var(--text-sub); text-transform: uppercase; letter-spacing: 0.5px; }}
        .filter-bar {{ display: flex; gap: 12px; margin-bottom: 20px; }}
        .search-box {{ flex: 1; padding: 10px 16px; border-radius: 10px; border: 1px solid var(--border); background: var(--card-bg); color: var(--text-main); font-size: 14px; }}
        .data-table-card {{ background: var(--card-bg); backdrop-filter: blur(20px); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.04); }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 14px; }}
        th {{ background: rgba(0,0,0,0.03); padding: 14px 18px; color: var(--text-sub); font-size: 12px; font-weight: 600; text-transform: uppercase; border-bottom: 1px solid var(--border); }}
        td {{ padding: 16px 18px; border-bottom: 1px solid var(--border); vertical-align: top; }}
        tr:last-child td {{ border-bottom: none; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 8px; font-size: 11px; font-weight: 600; }}
        .platform-reddit {{ background: #ff45001a; color: #ff4500; }}
        .platform-twitter {{ background: #1d9bf01a; color: #1d9bf0; }}
        .platform-instagram {{ background: #e1306c1a; color: #e1306c; }}
        .platform-youtube {{ background: #ff00001a; color: #ff0000; }}
        .platform-tiktok {{ background: #00f2fe1a; color: #00b4d8; }}
        .badge.metric {{ background: rgba(134, 134, 139, 0.15); color: var(--text-main); margin: 2px; }}
        .post-title {{ font-weight: 600; font-size: 15px; margin-bottom: 4px; }}
        .post-text {{ font-size: 13px; line-height: 1.5; color: var(--text-main); white-space: pre-line; }}
        .tag {{ color: var(--accent); font-size: 12px; margin-right: 6px; }}
        .thumb {{ width: 50px; height: 50px; border-radius: 8px; object-fit: cover; margin: 4px 4px 0 0; border: 1px solid var(--border); }}
        .post-link {{ font-size: 12px; color: var(--accent); text-decoration: none; margin-top: 6px; display: inline-block; }}
        .date-col {{ font-size: 12px; color: var(--text-sub); white-space: nowrap; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Bulk Social Media Scraper</h1>
                <div class="subtitle">Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')} &bull; macOS Optimized Report</div>
            </div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-num">{len(items)}</span>
                <span class="stat-label">Total Items</span>
            </div>
            <div class="stat-card">
                <span class="stat-num">{total_media}</span>
                <span class="stat-label">Media Attachments</span>
            </div>
            {platform_summary}
        </div>

        <div class="filter-bar">
            <input type="text" id="searchInput" class="search-box" placeholder="Filter by keyword, author, or platform..." onkeyup="filterTable()">
        </div>

        <div class="data-table-card">
            <table id="resultsTable">
                <thead>
                    <tr>
                        <th style="width: 110px;">Platform</th>
                        <th style="width: 160px;">Author / Target</th>
                        <th>Content & Media</th>
                        <th style="width: 180px;">Engagement</th>
                        <th style="width: 110px;">Date</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows_html)}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function filterTable() {{
            const input = document.getElementById("searchInput").value.toLowerCase();
            const rows = document.querySelectorAll(".item-row");
            rows.forEach(row => {{
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(input) ? "" : "none";
            }});
        }}
    </script>
</body>
</html>
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info("Exported HTML report: %s", filepath)
        return filepath

    def export_all(
        self, items: List[ScrapedItem], formats: List[str] = None, prefix: str = "bulk_export"
    ) -> Dict[str, str]:
        """Convenience method to export into multiple formats at once."""
        formats = formats or ["csv", "json", "sqlite", "html"]
        exported_files = {}

        if "csv" in formats:
            exported_files["csv"] = self.export_csv(items, prefix=prefix)
        if "json" in formats:
            exported_files["json"] = self.export_json(items, prefix=prefix)
        if "jsonl" in formats:
            exported_files["jsonl"] = self.export_json(items, prefix=prefix, jsonl=True)
        if "sqlite" in formats:
            exported_files["sqlite"] = self.export_sqlite(items)
        if "html" in formats:
            exported_files["html"] = self.export_html_report(items, prefix=prefix)

        return exported_files
