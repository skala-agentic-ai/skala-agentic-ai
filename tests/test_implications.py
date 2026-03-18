# MODIFIED: SUMMARY/종합시사점 프롬프트 고도화
from __future__ import annotations

import json
import re
import unittest

from agents.report_writer.implications import generate


class TestImplications(unittest.TestCase):
    def test_three_paragraphs(self) -> None:
        out = generate("lges", "catl", "cmp", "swot", "market", run_id="imp1")
        paragraphs = [p for p in out.split("\n\n") if p.strip()]
        self.assertEqual(len(paragraphs), 3)

    def test_each_paragraph_at_least_4_sentences(self) -> None:
        out = generate("lges", "catl", "cmp", "swot", "market", run_id="imp2")
        paragraphs = [p for p in out.split("\n\n") if p.strip()]
        for p in paragraphs:
            self.assertGreaterEqual(p.count("."), 4)

    def test_no_bullet_and_no_inline_citation(self) -> None:
        mock = lambda *_args, **_kwargs: json.dumps(
            {
                "paragraph_1": "문장1. 문장2. 문장3. 문장4. [출처, 2026]",
                "paragraph_2": "문장1. 문장2. 문장3. 문장4.",
                "paragraph_3": "문장1. 문장2. 문장3. 문장4. 해야 한다.",
            },
            ensure_ascii=False,
        )
        out = generate("lges", "catl", "cmp", "swot", "market", run_id="imp3", llm_call=mock)
        self.assertFalse(any(ln.strip().startswith("- ") for ln in out.splitlines()))
        self.assertIsNone(re.search(r"\[.+?,\s*\d{4}\]", out))

    def test_paragraph3_action_phrase(self) -> None:
        out = generate("lges", "catl", "cmp", "swot", "market", run_id="imp4")
        p3 = [p for p in out.split("\n\n") if p.strip()][2]
        self.assertTrue(("해야 한다" in p3) or ("필요하다" in p3))

    def test_failure_marker_on_llm_error(self) -> None:
        def bad(*_args, **_kwargs):
            raise RuntimeError("boom")

        out = generate("lges", "catl", "cmp", "swot", "market", run_id="imp5", llm_call=bad)
        self.assertTrue(out.startswith("종합 시사점 생성 실패"))


if __name__ == "__main__":
    unittest.main()
