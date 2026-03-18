from __future__ import annotations

import io
import logging
import unittest
from unittest.mock import patch

from pipeline import run_pipeline
from runtime import get_logger
from schemas import new_company_state


class TestPhase8To9Integration(unittest.TestCase):
    def test_end_to_end_query_1(self) -> None:
        state = run_pipeline("LGES와 CATL 전략 비교", run_id="e2e1")
        self.assertTrue(state["report_path"])
        self.assertIn("# SUMMARY", state["final_report"])
        self.assertIn("# REFERENCE", state["final_report"])

    def test_end_to_end_query_2(self) -> None:
        state = run_pipeline("북미 정책 변화가 배터리에 미치는 영향", run_id="e2e2")
        self.assertIn("# 1. 시장 배경", state["final_report"])
        self.assertIn("# 6. 종합 시사점", state["final_report"])

    def test_router_to_three_agents_mapping(self) -> None:
        state = run_pipeline("라우팅 검증", run_id="route1")
        routes = state["task_routes"]
        self.assertTrue(all(k in routes for k in ("market", "lges", "catl")))

    def test_review_entry_requires_all_approved(self) -> None:
        bad = new_company_state()
        bad["approved"] = False
        ok = new_company_state()
        ok["approved"] = True

        with patch("pipeline.execute_parallel", return_value=(ok, bad, ok)):
            state = run_pipeline("승인 조건", run_id="appr1")
            self.assertIn("Force Exit", state["retry_instruction"])

    def test_quality_gate_fail_reloops(self) -> None:
        with patch("pipeline.quality_judge", side_effect=[(False, "retry"), (True, "")]):
            state = run_pipeline("재루프", run_id="loop1")
            self.assertTrue(state["report_path"])

    def test_reportwriter_to_finaloutput_transition(self) -> None:
        state = run_pipeline("전이 검증", run_id="status1")
        self.assertTrue(state["final_report"])
        self.assertTrue(state["report_path"])

    def test_run_id_in_logs(self) -> None:
        stream = io.StringIO()
        logger = get_logger("log123")
        for h in list(logger.handlers):
            logger.removeHandler(h)
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("run_id=%(run_id)s %(message)s"))
        logger.addHandler(handler)
        logger.info("hello")
        self.assertIn("run_id=log123", stream.getvalue())

    def test_state_pollution_guard(self) -> None:
        state = run_pipeline("state test", run_id="state1")
        self.assertNotIn("company_state", state)


if __name__ == "__main__":
    unittest.main()
