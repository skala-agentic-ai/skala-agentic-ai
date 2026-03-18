# MODIFIED: web 레퍼런스 표시명/필터/중복제거 검증 추가
from __future__ import annotations

import unittest

from agents.report_writer.reference_compiler import (
    _filter_valid_refs,
    compile,
    format_reference_entry,
    render_reference_section,
)
from schemas import new_company_state


class TestReferenceCompiler(unittest.TestCase):
    def test_compiler_reads_evidence_references_not_draft(self) -> None:
        c1 = new_company_state()
        c1["draft"] = "본문 [가짜, 2026]"
        c1["evidence_references"] = [{"source": "DocA.pdf", "page": "1", "year": "2026"}]
        refs = compile([c1])
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["source"], "DocA.pdf")

    def test_dedup_by_source_page(self) -> None:
        c1 = new_company_state()
        c2 = new_company_state()
        c1["evidence_references"] = [{"source": "DocA.pdf", "page": "1", "year": "2026"}]
        c2["evidence_references"] = [{"source": "DocA.pdf", "page": "1", "year": "2026"}]
        refs = compile([c1, c2])
        self.assertEqual(len(refs), 1)

    def test_empty_evidence_references(self) -> None:
        c1 = new_company_state()
        refs = compile([c1])
        self.assertEqual(refs, [])

    def test_web_source_uses_title_not_url_fragment(self) -> None:
        ref = {
            "source_type": "web",
            "title": "2026 배터리 시장 전망 분석",
            "source_url": "https://example.com/articleView.html?idxno=125870",
            "year": "2026",
        }
        out = format_reference_entry(ref)
        self.assertNotIn("idxno", out)
        self.assertIn("2026 배터리 시장 전망 분석", out)

    def test_web_source_fallback_to_domain_when_no_title(self) -> None:
        ref = {
            "source_type": "web",
            "title": "",
            "source_url": "https://news.example.com/article/123?f=p",
            "year": "2026",
        }
        out = format_reference_entry(ref)
        self.assertIn("news.example.com", out)
        self.assertNotIn("idxno", out)

    def test_empty_ref_list_filtered(self) -> None:
        refs = [[], None, {}, {"source": "valid.pdf", "year": "2026"}]
        filtered = _filter_valid_refs(refs)
        self.assertEqual(len(filtered), 1)

    def test_deduplication_by_display_name(self) -> None:
        refs = [
            {"source_type": "web", "title": "동일 제목으로 처리되는 웹 레퍼런스", "year": "2026"},
            {"source_type": "web", "title": "동일 제목으로 처리되는 웹 레퍼런스", "year": "2026"},
        ]
        rendered = render_reference_section(refs)
        self.assertEqual(rendered.count("동일 제목으로 처리되는 웹 레퍼런스"), 1)

    def test_format_reference_entry_missing_page(self) -> None:
        out = format_reference_entry({"source": "A.pdf", "year": "2026"})
        self.assertEqual(out, "- A.pdf (2026)")


if __name__ == "__main__":
    unittest.main()
