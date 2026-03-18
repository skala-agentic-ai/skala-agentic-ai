# MODIFIED: SUMMARY bullet 완결성 및 truncation 방지 검증
from __future__ import annotations

import json
import re
import unittest
from unittest.mock import Mock

from agents.report_writer.summary import _is_complete_sentence, generate


class TestSummary(unittest.TestCase):
    @staticmethod
    def _extract_bullets(output: str) -> list[str]:
        return [ln[2:] for ln in output.splitlines() if ln.strip().startswith("- ")]

    def test_exactly_4_bullets(self) -> None:
        out = generate("lges", "catl", "cmp", "market", run_id="sum1")
        bullets = self._extract_bullets(out)
        self.assertEqual(len(bullets), 4)

    def test_topic_keywords_covered(self) -> None:
        out = generate("북미 BaaS", "도메인 인프라", "경쟁 로드맵", "캐즘 수요", run_id="sum2")
        self.assertTrue("캐즘" in out or "수요" in out)
        self.assertTrue("북미" in out or "BaaS" in out)
        self.assertTrue("도메인" in out or "인프라" in out)
        self.assertTrue("경쟁" in out or "로드맵" in out)

    def test_no_inline_citation(self) -> None:
        mock = Mock(return_value=json.dumps({"bullets": [
            "전기차 캐즘 대응: 문장 [출처, 2026] 문장.",
            "LGES 전략: 문장.",
            "CATL 전략: 문장.",
            "경쟁력 진단: 문장.",
        ]}, ensure_ascii=False))
        out = generate("lges", "catl", "cmp", "market", run_id="sum3", llm_call=mock)
        self.assertIsNone(re.search(r"\[.+?,\s*\d{4}\]", out))

    def test_llm_called_with_4_inputs(self) -> None:
        def fake(system_prompt: str, user_payload: str, run_id: str, **kwargs):
            self.assertIn("[LGES 분석]", user_payload)
            self.assertIn("[CATL 분석]", user_payload)
            self.assertIn("[핵심 전략 비교]", user_payload)
            self.assertIn("[시장 배경]", user_payload)
            self.assertEqual(kwargs.get("max_tokens"), 1000)
            return {
                "bullets": [
                    "전기차 캐즘 대응: 완결된 문장이다.",
                    "LGES 전략: 완결된 문장이다.",
                    "CATL 전략: 완결된 문장이다.",
                    "경쟁력 진단: 완결된 문장이다.",
                ]
            }

        out = generate("lges", "catl", "cmp", "market", run_id="sum4", llm_call=fake)
        self.assertEqual(len([ln for ln in out.splitlines() if ln.startswith("- ")]), 4)

    def test_failure_marker_on_llm_error(self) -> None:
        def bad(*_args, **_kwargs):
            raise RuntimeError("boom")

        out = generate("lges", "catl", "cmp", "market", run_id="sum5", llm_call=bad)
        self.assertTrue(out.startswith("SUMMARY 생성 실패"))

    def test_no_truncated_bullets(self) -> None:
        out = generate("lges", "catl", "cmp", "market", run_id="sum6")
        bullets = self._extract_bullets(out)
        self.assertEqual(len(bullets), 4)
        self.assertTrue(all(b.strip()[-1] in ("다", ".", "?", "!") for b in bullets))

    def test_complete_sentence_helper(self) -> None:
        self.assertFalse(_is_complete_sentence("경쟁력 진단: 수익성 지표 결합에서"))
        self.assertTrue(_is_complete_sentence("경쟁력 진단: 수익성 지표 결합에서 결정된다."))


if __name__ == "__main__":
    unittest.main()
