# MODIFIED: LGES/CATL 500자 분량, 재시도, evidence 직렬화 검증 추가
from __future__ import annotations

import json
import re
import unittest

from agents.common.content_writer import (
    MAX_EVIDENCE_CHARS,
    _is_sufficient_length,
    _serialize_evidence,
    write,
)
from schemas import new_company_state


class TestContentWriter(unittest.TestCase):
    def _evidence(self) -> list[dict]:
        return [
            {
                "source_type": "pdf",
                "source_url": "/tmp/a.pdf#page=1",
                "published_at": "2026-01-01",
                "retrieved_at": "2026-03-18",
                "source_name": "A.pdf",
                "domain": "market",
                "title": "A",
                "excerpt": "2026년 글로벌 배터리 시장은 전기차 수요 정체와 ESS 확장이 동시에 발생하며 북미 정책 변화가 공급망 재편을 가속화한다.",
                "year": "2026",
            },
            {
                "source_type": "pdf",
                "source_url": "/tmp/b.pdf#page=2",
                "published_at": "2026-01-01",
                "retrieved_at": "2026-03-18",
                "source_name": "B.pdf",
                "domain": "market",
                "title": "B",
                "excerpt": "기업들은 원가 압력 대응을 위해 생산지 분산과 제품 포트폴리오 조정을 병행하고 있으며 실행 속도가 수익성 차이를 만든다.",
                "year": "2026",
            },
        ]

    def test_no_inline_citation_pattern(self) -> None:
        st = new_company_state()
        draft = write(self._evidence(), "1. 시장 배경", company_state=st, run_id="cw1", agent_name="market")
        self.assertIsNone(re.search(r"\[.+?,\s*\d{4}\]", draft))

    def test_not_verbatim_substring_of_evidence(self) -> None:
        st = new_company_state()
        draft = write(self._evidence(), "1. 시장 배경", company_state=st, run_id="cw2", agent_name="market")
        for ev in self._evidence():
            self.assertNotIn(ev["excerpt"], draft)

    def test_paragraph_count_and_references(self) -> None:
        st = new_company_state()
        draft = write(self._evidence(), "1. 시장 배경", company_state=st, run_id="cw3", agent_name="market")
        paragraphs = [p for p in draft.split("\n\n") if p.strip()]
        self.assertGreaterEqual(len(paragraphs), 2)
        self.assertTrue(st["evidence_references"])

    def test_lges_draft_exceeds_500_chars(self) -> None:
        st = new_company_state()

        def mock_llm(*_args, **_kwargs):
            long_text = "LG에너지솔루션 전략 분석 문장입니다. " * 80
            return {"prose": long_text, "references": [{"source": "A.pdf", "page": "p.1", "year": "2026"}]}

        draft = write(
            evidence_pool=self._evidence(),
            section_scope="2.1~2.4 LGES 전략 분석",
            company_state=st,
            run_id="cw4",
            agent_name="lges",
            llm_call=mock_llm,
        )
        self.assertTrue(_is_sufficient_length(draft))

    def test_catl_draft_exceeds_500_chars(self) -> None:
        st = new_company_state()

        def mock_llm(*_args, **_kwargs):
            long_text = "CATL 전략 분석 문장입니다. " * 90
            return {"prose": long_text, "references": [{"source": "B.pdf", "page": "p.2", "year": "2026"}]}

        draft = write(
            evidence_pool=self._evidence(),
            section_scope="3.1~3.4 CATL 전략 분석",
            company_state=st,
            run_id="cw5",
            agent_name="catl",
            llm_call=mock_llm,
        )
        self.assertTrue(_is_sufficient_length(draft))

    def test_retry_triggered_when_draft_too_short(self) -> None:
        st = new_company_state()
        call_count = {"n": 0}

        def mock_llm(*_args, **_kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return '{"prose": "짧은내용", "references": []}'
            return json.dumps(
                {"prose": ("충분히 긴 내용입니다. " * 60), "references": []},
                ensure_ascii=False,
            )

        draft = write(
            evidence_pool=self._evidence(),
            section_scope="2.1~2.4 LGES 전략 분석",
            company_state=st,
            run_id="cw6",
            agent_name="lges",
            llm_call=mock_llm,
        )
        self.assertEqual(call_count["n"], 2)
        self.assertTrue(_is_sufficient_length(draft))

    def test_evidence_serialization_respects_max_chars(self) -> None:
        docs = []
        for i in range(10):
            docs.append(
                {
                    "source_type": "web",
                    "source_url": f"https://x/{i}",
                    "published_at": "2026-01-01",
                    "retrieved_at": "2026-03-18",
                    "source_name": f"S{i}",
                    "domain": "LGES",
                    "title": f"T{i}",
                    "excerpt": "x" * 1000,
                    "year": "2026",
                    "content": "x" * 1000,
                }
            )
        result = _serialize_evidence(docs)
        self.assertLessEqual(len(result), MAX_EVIDENCE_CHARS + 200)

    def test_empty_evidence_pool_returns_failure_marker(self) -> None:
        draft = write(
            evidence_pool=[],
            section_scope="2.1~2.4 LGES 전략 분석",
            agent_name="lges",
            run_id="cw7",
        )
        self.assertIn("섹션 생성 실패", draft)


if __name__ == "__main__":
    unittest.main()
