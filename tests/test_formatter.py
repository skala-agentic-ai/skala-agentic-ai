# MODIFIED: 섹션 2/3 소제목 분리 및 REFERENCE URL/빈항목 정규화 검증
from __future__ import annotations

import re
import unittest

from agents.supervisor.formatter import format
from schemas import new_report_draft


class TestFormatter(unittest.TestCase):
    def _draft(self):
        d = new_report_draft()
        d["summary"] = "- 요약 [출처, 2026]"
        d["market_background"] = "문단 A [시장, 2026]\n\n문단 B"
        d["lges_analysis"] = (
            "2.1 LGES 핵심 전략 본문.\n\n"
            "2.2 LGES 수익성 본문.\n\n"
            "2.3 LGES 긍정 근거 본문.\n\n"
            "2.4 LGES 리스크 본문."
        )
        d["catl_analysis"] = (
            "3.1 CATL 핵심 전략 본문.\n\n"
            "3.2 CATL 수익성 본문.\n\n"
            "3.3 CATL 긍정 근거 본문.\n\n"
            "3.4 CATL 리스크 본문."
        )
        d["comparison_matrix"] = {"시장포지셔닝": {"lges": "l", "catl": "c"}}
        d["swot"] = {
            "lges": {"S": "s", "W": "w", "O": "o", "T": "t"},
            "catl": {"S": "s2", "W": "w2", "O": "o2", "T": "t2"},
        }
        d["implications"] = "시사점 [근거, 2026]"
        d["reference"] = [
            {"source": "2026 배터리 시장 전망 보고서.pdf p.1", "page": "p.1", "year": "2026", "source_type": "pdf"},
            {"source": "2026 배터리 시장 전망 보고서.pdf p.2", "page": "p.2", "year": "2026", "source_type": "pdf"},
            {"source_type": "web", "title": "연합뉴스 배터리 시장 전망", "source_url": "https://example.com/articleView.html?idxno=125870", "year": "2026"},
            {"source": "[]", "year": ""},
            {},
        ]
        d["status"] = "validated"
        return d

    def test_strip_citations_from_summary_sections_and_implications(self) -> None:
        md = format(self._draft())
        body = md.split("## REFERENCE", 1)[0]
        self.assertIsNone(re.search(r"\[.+?,\s*\d{4}\]", body))

    def test_swot_table_format(self) -> None:
        md = format(self._draft())
        self.assertIn("| 구분 | LGES | CATL |", md)

    def test_title_block_present(self) -> None:
        md = format(self._draft(), run_id="rid-123")
        self.assertTrue(md.startswith("# 배터리 시장 전략 분석 보고서"))
        self.assertIn("> **분석 기준일:**", md)
        self.assertNotIn("> **Run ID:**", md)
        self.assertIn("---", md.split("## SUMMARY")[0])

    def test_reference_format_normalized(self) -> None:
        md = format(self._draft())
        reference_body = md.split("## REFERENCE", 1)[1]
        self.assertNotIn("idxno=", reference_body)
        self.assertNotIn("?view=", reference_body)
        self.assertNotIn("?f=p", reference_body)
        self.assertNotIn("[]", reference_body)
        self.assertIsNone(re.search(r"\.pdf p\.\d+", reference_body))
        self.assertEqual(reference_body.count("2026 배터리 시장 전망 보고서.pdf"), 1)

    def test_lges_section_has_subsection_headers(self) -> None:
        md = format(self._draft())
        for header in ["### 2.1", "### 2.2", "### 2.3", "### 2.4"]:
            self.assertIn(header, md)

    def test_catl_section_has_subsection_headers(self) -> None:
        md = format(self._draft())
        for header in ["### 3.1", "### 3.2", "### 3.3", "### 3.4"]:
            self.assertIn(header, md)

    def test_subsection_dividers_present(self) -> None:
        md = format(self._draft())
        lges_block = md.split("## 3.", 1)[0]
        self.assertGreaterEqual(lges_block.count("---"), 3)

    def test_reference_no_empty_entries(self) -> None:
        md = format(self._draft())
        ref_block = md.split("## REFERENCE", 1)[1]
        for line in ref_block.strip().splitlines():
            if line.startswith("- "):
                self.assertGreater(len(line.strip()), 5)


if __name__ == "__main__":
    unittest.main()
