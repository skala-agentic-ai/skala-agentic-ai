# MODIFIED: web search SerpAPI 전용 경로 테스트로 정렬
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from retrieval import pdf_loader
from retrieval.pdf_loader import load_pdfs_from_dir
from retrieval.vector_store import ingest, query, reset_store
from retrieval.web_search import search
from schemas import ValidationError


class TestPhase1Data(unittest.TestCase):
    def setUp(self) -> None:
        reset_store()

    def test_pdf_loader_lges_catl_market(self) -> None:
        self.assertGreater(len(load_pdfs_from_dir("data/LGES", "LGES")), 0)
        self.assertGreater(len(load_pdfs_from_dir("data/CATL", "CATL")), 0)
        self.assertGreater(len(load_pdfs_from_dir("data/market", "market")), 0)

    def test_pdf_loader_max_pages_skip(self) -> None:
        with patch.object(pdf_loader, "MAX_INGEST_PAGES", 1):
            docs = load_pdfs_from_dir("data/LGES", "LGES")
            self.assertLessEqual(len(docs), 1)

    def test_pdf_loader_corrupted_skip(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "LGES"
            p.mkdir()
            (p / "bad.pdf").write_bytes(b"not-a-pdf")
            docs = load_pdfs_from_dir(p, "LGES")
            self.assertEqual(docs, [])

    def test_pdf_loader_cross_ingest_blocked(self) -> None:
        with self.assertRaises(ValidationError):
            load_pdfs_from_dir("data/LGES", "CATL")

    def test_vector_store_ingest_query_and_domain_isolation(self) -> None:
        lges_docs = load_pdfs_from_dir("data/LGES", "LGES")
        ingest("LGES", lges_docs)
        out = query("LGES", ["Research"])
        self.assertGreater(len(out), 0)
        self.assertEqual(query("CATL", ["Research"]), [])

    def test_vector_store_empty_ingest_error(self) -> None:
        with self.assertRaises(RuntimeError):
            ingest("LGES", [])

    def test_web_search_schema_and_fail(self) -> None:
        class FakeSearch:
            def __init__(self, _params):
                pass

            def get_dict(self):
                return {
                    "organic_results": [
                        {
                            "link": "https://example.com/battery",
                            "title": "Battery",
                            "snippet": "battery market",
                            "date": "2026-01-01",
                        }
                    ]
                }

        with patch.dict("os.environ", {"SERP_API_KEY": "fake-key"}, clear=False):
            with patch("serpapi.GoogleSearch", new=FakeSearch):
                out = search(["battery"])
                self.assertGreater(len(out), 0)
                self.assertIn("source_type", out[0])
                self.assertEqual(search(["battery"], force_fail=True), [])

    def test_web_search_tavily_result_structure(self) -> None:
        class FakeSearch:
            def __init__(self, _params):
                pass

            def get_dict(self):
                return {
                    "organic_results": [
                        {
                            "link": "https://example.com/battery-2026",
                            "title": "2026 Battery Market Report",
                            "snippet": "Global battery market shows...",
                            "date": "2026-01-15",
                        }
                    ]
                }

        with patch.dict("os.environ", {"SERP_API_KEY": "fake-key"}, clear=False):
            with patch("serpapi.GoogleSearch", new=FakeSearch):
                results = search(["battery market 2026"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_type"], "web")
        self.assertEqual(results[0]["source_url"], "https://example.com/battery-2026")
        self.assertNotEqual(results[0].get("content", ""), "")
        self.assertNotEqual(results[0]["excerpt"], "")
        self.assertIsNotNone(results[0]["retrieved_at"])

    def test_web_search_no_api_key_raises(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(
                EnvironmentError, "SERP_API_KEY"
            ):
                search(["test query"])

    def test_web_search_partial_failure_continues(self) -> None:
        call_count = {"n": 0}

        class FakeSearch:
            def __init__(self, params):
                self.query = params.get("q", "")

            def get_dict(self):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise Exception("simulated timeout")
                return {
                    "organic_results": [
                        {
                            "link": "https://ok.com",
                            "title": "ok",
                            "snippet": "ok content",
                            "date": None,
                        }
                    ]
                }

        with patch.dict("os.environ", {"SERP_API_KEY": "fake-key"}, clear=False):
            with patch("serpapi.GoogleSearch", new=FakeSearch):
                results = search(["fail query", "ok query"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_url"], "https://ok.com")

    def test_web_search_filters_empty_urls(self) -> None:
        class FakeSearch:
            def __init__(self, _params):
                pass

            def get_dict(self):
                return {
                    "organic_results": [
                        {"link": "", "title": "no url", "snippet": "x"},
                        {"link": "https://valid.com", "title": "valid", "snippet": "y"},
                    ]
                }

        with patch.dict("os.environ", {"SERP_API_KEY": "fake-key"}, clear=False):
            with patch("serpapi.GoogleSearch", new=FakeSearch):
                results = search(["test"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_url"], "https://valid.com")


if __name__ == "__main__":
    unittest.main()
