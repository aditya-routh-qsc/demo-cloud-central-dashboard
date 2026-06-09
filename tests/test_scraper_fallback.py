from __future__ import annotations

import json
import csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scraper import scrape_schedule, save_to_json, save_to_csv


class ScraperFallbackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("scraper.async_playwright")
    async def test_scrape_schedule_fails_no_fallback(self, mock_playwright) -> None:
        # Arrange: Make browser launch or navigation raise an exception
        mock_playwright.side_effect = RuntimeError("Playwright launch failed")

        # Act
        result = await scrape_schedule("https://example.com/schedule", fallback_path=None)

        # Assert
        self.assertEqual(result, [])

    @patch("scraper.async_playwright")
    async def test_scrape_schedule_fails_json_fallback_success(self, mock_playwright) -> None:
        # Arrange: Pre-populate fallback JSON file
        fallback_file = self.temp_path / "infocomm_india.json"
        previous_data = [
            {
                "date": "Mon, June 15",
                "title": "Previous Session",
                "duration": "10:00 - 11:00",
                "location": "Room 1",
                "link": "https://example.com/session1",
                "description": "Previous description"
            }
        ]
        save_to_json(previous_data, fallback_file)

        # Make scraper fail
        mock_playwright.side_effect = RuntimeError("Failed to load page")

        # Act
        result = await scrape_schedule("https://example.com/schedule", fallback_path=fallback_file)

        # Assert
        self.assertEqual(result, previous_data)

    @patch("scraper.async_playwright")
    async def test_scrape_schedule_fails_csv_fallback_success(self, mock_playwright) -> None:
        # Arrange: Pre-populate fallback CSV file
        fallback_file = self.temp_path / "infocomm_india.csv"
        previous_data = [
            {
                "date": "Mon, June 15",
            }
        ]
        save_to_csv(previous_data, fallback_file)

        # Make scraper fail
        mock_playwright.side_effect = RuntimeError("Failed to extract data")

        # Act
        result = await scrape_schedule("https://example.com/schedule", fallback_path=fallback_file)

        # Assert
        # DictReader returns string keys and values, which matches previous_data structures.
        self.assertEqual(result, previous_data)

    @patch("scraper.async_playwright")
    async def test_scrape_schedule_fails_fallback_file_not_exist(self, mock_playwright) -> None:
        # Arrange: Non-existent fallback path
        fallback_file = self.temp_path / "does_not_exist.json"
        mock_playwright.side_effect = RuntimeError("Playwright error")

        # Act
        result = await scrape_schedule("https://example.com/schedule", fallback_path=fallback_file)

        # Assert
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
