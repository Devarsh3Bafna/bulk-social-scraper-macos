import unittest
import os
import tempfile
import json
import sqlite3

from scraper.core.base import ScrapedItem
from scraper.core.session import ResilientSession
from scraper.core.exporter import DataExporter
from scraper.core.downloader import MediaDownloader
from scraper.core.macos_notifier import MacOSNotifier
from scraper.core.orchestrator import BulkOrchestrator
from scraper.platforms import detect_platform_from_url


class TestBulkScraper(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_items = [
            ScrapedItem(
                id="post_1",
                platform="reddit",
                target="technology",
                author="u/test_user",
                title="Apple Releases New M4 Pro Chip",
                text="The performance gains are substantial.",
                url="https://www.reddit.com/r/technology/comments/1",
                timestamp="2026-10-14T00:00:00Z",
                metrics={"upvotes": 1250, "comments": 85},
                media_urls=["https://example.com/image1.jpg"],
                tags=["Tech", "Hardware"],
            ),
            ScrapedItem(
                id="post_2",
                platform="twitter",
                target="openai",
                author="@openai",
                title="Update on AI models",
                text="Announcing our latest reasoning updates.",
                url="https://x.com/openai/status/123",
                timestamp="2026-10-14T01:00:00Z",
                metrics={"likes": 4200, "retweets": 810},
                media_urls=[],
                tags=["AI"],
            ),
        ]

    def test_scraped_item_model(self):
        item = self.sample_items[0]
        flat = item.to_flat_dict()
        self.assertEqual(flat["id"], "post_1")
        self.assertEqual(flat["metric_upvotes"], 1250)
        self.assertIn("image1.jpg", flat["media_urls"])

    def test_exporter_csv(self):
        exporter = DataExporter(output_dir=self.temp_dir)
        csv_path = exporter.export_csv(self.sample_items, prefix="test_export")
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
            self.assertIn("Apple Releases New M4 Pro Chip", content)
            self.assertIn("metric_upvotes", content)

    def test_exporter_json(self):
        exporter = DataExporter(output_dir=self.temp_dir)
        json_path = exporter.export_json(self.sample_items, prefix="test_export")
        self.assertTrue(os.path.exists(json_path))
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["id"], "post_1")

    def test_exporter_sqlite(self):
        exporter = DataExporter(output_dir=self.temp_dir)
        db_path = exporter.export_sqlite(self.sample_items)
        self.assertTrue(os.path.exists(db_path))

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, platform, title FROM scraped_posts")
        rows = cur.fetchall()
        conn.close()

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0][0], "post_1")
        self.assertEqual(rows[0][1], "reddit")

    def test_exporter_html_report(self):
        exporter = DataExporter(output_dir=self.temp_dir)
        html_path = exporter.export_html_report(self.sample_items, prefix="test_report")
        self.assertTrue(os.path.exists(html_path))
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("Apple Releases New M4 Pro Chip", content)
            self.assertIn("Bulk Social Media Scraper", content)

    def test_detect_platform_from_url(self):
        self.assertEqual(detect_platform_from_url("https://www.reddit.com/r/apple/"), "reddit")
        self.assertEqual(detect_platform_from_url("https://twitter.com/mkbhd"), "twitter")
        self.assertEqual(detect_platform_from_url("https://x.com/elonmusk"), "twitter")
        self.assertEqual(detect_platform_from_url("https://www.youtube.com/watch?v=1234"), "youtube")
        self.assertEqual(detect_platform_from_url("https://www.instagram.com/apple/"), "instagram")
        self.assertEqual(detect_platform_from_url("https://www.tiktok.com/@tiktok"), "tiktok")
        self.assertEqual(detect_platform_from_url("https://www.pinterest.com/pin/123"), "pinterest")

    def test_session_user_agents(self):
        session = ResilientSession()
        ua = session.get_random_user_agent()
        self.assertIn("Macintosh", ua)

    def test_downloader_filename_sanitizer(self):
        downloader = MediaDownloader(download_dir=self.temp_dir)
        safe = downloader._sanitize_name('test/invalid:name*here?.png')
        self.assertNotIn("/", safe)
        self.assertNotIn(":", safe)
        self.assertNotIn("*", safe)

    def test_batch_file_parsing(self):
        sample_csv = os.path.join(self.temp_dir, "batch.csv")
        with open(sample_csv, "w", encoding="utf-8") as f:
            f.write("platform,target,limit\nreddit,technology,10\ntwitter,openai,5\n")

        orchestrator = BulkOrchestrator()
        targets = orchestrator.parse_batch_file(sample_csv)
        self.assertEqual(len(targets), 2)
        self.assertEqual(targets[0]["platform"], "reddit")
        self.assertEqual(targets[0]["limit"], 10)
        self.assertEqual(targets[1]["platform"], "twitter")
        self.assertEqual(targets[1]["limit"], 5)


if __name__ == "__main__":
    unittest.main()
