# MODIFIED: Updated report-writer tests for new swot/reference interfaces and per-company state inputs.
from __future__ import annotations

import os
import unittest
from pathlib import Path

from agents.supervisor.global_consistency import check as consistency_check
from agents.supervisor.quality_gate import judge
from agents.supervisor.final_synth import synthesize
from agents.report_writer.comparison_matrix import generate as gen_matrix
from agents.report_writer.swot import generate as gen_swot
from agents.report_writer.implications import generate as gen_imp
from agents.report_writer.summary import generate as gen_summary
from agents.report_writer.reference_compiler import compile as compile_refs
from agents.report_writer.agent import run as run_report_writer
from agents.supervisor.final_validation import validate
from agents.supervisor.formatter import format as md_format, FormattingError
from agents.supervisor.report_saver import save
from schemas import new_company_state, new_global_state, new_report_draft


class TestPhase5To7(unittest.TestCase):
    def _company(self, text: str):
        c = new_company_state()
        c["draft"] = text
        c["approved"] = True
        return c

    def test_consistency_gate_and_synth(self) -> None:
        gs = new_global_state("r1")
        m = self._company("시장 2026 반대 [시장, 2026]")
        l = self._company("LGES 2026 반대 [LGES, 2026]")
        c = self._company("CATL 2026 반대 [CATL, 2026]")
        report = consistency_check(m, l, c, gs)
        self.assertEqual(gs["consistency_report"], report)
        passed, instruction = judge(report)
        self.assertTrue(passed)
        self.assertEqual(instruction, "")
        findings = synthesize(m, l, c, gs)
        self.assertIn("<<<MARKET>>>", findings)
        self.assertTrue(gs["macro_market_context"])

    def test_quality_gate_fail_instruction(self) -> None:
        passed, instruction = judge("연도 불일치")
        self.assertFalse(passed)
        self.assertTrue(instruction)

    def test_report_writer_components_and_agent(self) -> None:
        findings = (
            "<<<MARKET>>>\nA [시장자료, 2026]\n<<<END_MARKET>>>\n"
            "<<<LGES>>>\nB [LGES자료, 2026]\n<<<END_LGES>>>\n"
            "<<<CATL>>>\nC [CATL자료, 2026]\n<<<END_CATL>>>"
        )
        matrix = gen_matrix("LGES draft", "CATL draft", {}, {}, run_id="p57")
        self.assertTrue(all(k in matrix for k in ("시장포지셔닝", "핵심기술", "수익성", "실행력", "주요리스크")))
        swot = gen_swot("LGES evidence", "CATL evidence", findings, run_id="t1")
        self.assertTrue(all(k in swot["lges"] for k in ("S", "W", "O", "T")))
        imp = gen_imp(findings)
        self.assertNotIn("[", imp)
        summary = gen_summary(matrix, swot, imp)
        self.assertLessEqual(len(summary), 400)
        c1 = new_company_state()
        c1["evidence_references"] = [{"source": "DocA.pdf", "page": "1", "year": "2026"}]
        refs = compile_refs([c1])
        self.assertGreater(len(refs), 0)

        market = new_company_state()
        lges_state = new_company_state()
        catl_state = new_company_state()
        market["draft"] = "market"
        lges_state["draft"] = "lges"
        catl_state["draft"] = "catl"
        market["evidence_references"] = [{"source": "M.pdf", "page": "1", "year": "2026"}]
        lges_state["evidence_references"] = [{"source": "L.pdf", "page": "2", "year": "2026"}]
        catl_state["evidence_references"] = [{"source": "C.pdf", "page": "3", "year": "2026"}]
        draft = run_report_writer(findings, market, lges_state, catl_state, run_id="t2")
        self.assertEqual(draft["status"], "pending_validation")
        self.assertTrue(draft["market_background"])
        self.assertTrue(draft["lges_analysis"])
        self.assertTrue(draft["catl_analysis"])

    def test_final_validation_formatter_saver(self) -> None:
        market = new_company_state()
        lges_state = new_company_state()
        catl_state = new_company_state()
        market["draft"] = "market"
        lges_state["draft"] = "lges"
        catl_state["draft"] = "catl"
        market["evidence_references"] = [{"source": "M.pdf", "page": "1", "year": "2026"}]
        lges_state["evidence_references"] = [{"source": "L.pdf", "page": "2", "year": "2026"}]
        catl_state["evidence_references"] = [{"source": "C.pdf", "page": "3", "year": "2026"}]
        draft = run_report_writer(
            "<<<MARKET>>>\nA [시장자료, 2026]\n<<<END_MARKET>>>\n"
            "<<<LGES>>>\nB [LGES자료, 2026]\n<<<END_LGES>>>\n"
            "<<<CATL>>>\nC [CATL자료, 2026]\n<<<END_CATL>>>",
            market,
            lges_state,
            catl_state,
            run_id="t3",
        )
        ok, _ = validate(draft)
        self.assertTrue(ok)
        self.assertEqual(draft["status"], "validated")

        md = md_format(draft)
        self.assertLess(md.find("# SUMMARY"), md.find("# 1. 시장 배경"))
        self.assertLess(md.find("# 6. 종합 시사점"), md.find("# REFERENCE"))
        with self.assertRaises(FormattingError):
            md_format(None)

        gs = new_global_state("r1")
        p = save(md, "r1", gs)
        self.assertTrue(Path(p).exists())
        self.assertIn("outputs", p)
        self.assertTrue(p.endswith(".md"))
        self.assertTrue(gs["report_path"])

    def test_final_validation_failed_status(self) -> None:
        d = new_report_draft()
        d["status"] = "pending_validation"
        ok, failed = validate(d)
        self.assertFalse(ok)
        self.assertGreater(len(failed), 0)
        self.assertEqual(d["status"], "failed")


if __name__ == "__main__":
    unittest.main()
