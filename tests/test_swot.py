# MODIFIED: Tests generic-detection, company-specific terms, and retry behavior in SWOT generation.
from __future__ import annotations

import json
import unittest

from agents.report_writer.swot import generate, _is_generic


class TestSwot(unittest.TestCase):
    def test_is_generic_false_for_distinct_cells(self) -> None:
        self.assertFalse(_is_generic("LGES 북미 IRA 전략", "CATL 중국 유럽 확장"))

    def test_company_specific_terms_present(self) -> None:
        out = generate("LGES 북미 IRA", "CATL 중국 유럽", "global", run_id="sw1")
        terms_lges = ["LGES", "북미", "IRA"]
        terms_catl = ["CATL", "중국", "유럽"]
        self.assertTrue(any(t in out["lges"]["S"] for t in terms_lges))
        self.assertTrue(any(t in out["catl"]["S"] for t in terms_catl))

    def test_retry_triggered_when_generic_detected(self) -> None:
        calls = {"n": 0}

        def generic_then_distinct(prompt: str, payload: dict, run_id: str):
            calls["n"] += 1
            if calls["n"] == 1:
                same = "동일 문장 동일 문장 동일 문장"
                return json.dumps(
                    {
                        "lges": {"S": same, "W": same, "O": same, "T": same},
                        "catl": {"S": same, "W": same, "O": same, "T": same},
                    },
                    ensure_ascii=False,
                )
            return json.dumps(
                {
                    "lges": {"S": "LGES 북미 실행", "W": "LGES 원가", "O": "LGES ESS", "T": "LGES 수요"},
                    "catl": {"S": "CATL 중국 실행", "W": "CATL 규제", "O": "CATL 신흥", "T": "CATL 관세"},
                },
                ensure_ascii=False,
            )

        out = generate("lges", "catl", "global", run_id="sw2", llm_call=generic_then_distinct)
        self.assertEqual(calls["n"], 2)
        self.assertFalse(_is_generic(out["lges"]["S"], out["catl"]["S"]))


if __name__ == "__main__":
    unittest.main()
