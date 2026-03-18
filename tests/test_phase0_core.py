from __future__ import annotations

import unittest

import constants
from schemas import (
    ValidationError,
    new_global_state,
    new_report_draft,
    validate_report_status,
    validate_required_fields,
    validate_source_doc,
)
from state_ownership import can_write, SPEC_PRIORITY


class TestPhase0Core(unittest.TestCase):
    def test_constants_values(self) -> None:
        self.assertEqual(constants.MAX_LOOP, 5)
        self.assertEqual(constants.MAX_RETRY, 2)
        self.assertEqual(constants.LLM_TIMEOUT, 60)
        self.assertEqual(constants.PIPELINE_TIMEOUT, 300)
        self.assertEqual(constants.MAX_INGEST_PAGES, 100)
        self.assertEqual(constants.CHUNK_SIZE, 512)
        self.assertEqual(constants.CHUNK_OVERLAP, 64)

    def test_state_required_fields_validation(self) -> None:
        gs = new_global_state("run1")
        required = {
            "run_id",
            "user_query",
            "bias_queries",
            "task_routes",
            "macro_market_context",
            "global_findings",
            "comparison_matrix",
            "consistency_report",
            "retry_instruction",
            "final_report",
            "report_path",
        }
        validate_required_fields("GlobalState", gs, required)
        with self.assertRaises(ValidationError):
            validate_required_fields("GlobalState", {"run_id": "x"}, required)

    def test_report_status_allowed_values(self) -> None:
        for status in (None, "pending_validation", "validated", "failed"):
            validate_report_status(status)
        with self.assertRaises(ValidationError):
            validate_report_status("bad")

    def test_source_doc_validation(self) -> None:
        good = {
            "source_type": "pdf",
            "source_url": "x",
            "published_at": "2026-01-01",
            "retrieved_at": "2026-01-01",
            "source_name": "a",
            "domain": "market",
            "title": "t",
            "excerpt": "e",
            "year": "2026",
        }
        out = validate_source_doc(good)
        self.assertEqual(out["source_type"], "pdf")
        bad = dict(good)
        del bad["source_url"]
        with self.assertRaises(ValidationError):
            validate_source_doc(bad)

    def test_state_ownership(self) -> None:
        self.assertTrue(can_write("report_draft.status", "DraftComplete"))
        self.assertFalse(can_write("report_draft.status", "ReportWriter"))

    def test_spec_priority_fixed(self) -> None:
        self.assertEqual(SPEC_PRIORITY["state_transition"], "docs/final_state_diagram.md")
        self.assertEqual(SPEC_PRIORITY["toc_and_section_scope"], "docs/final_flowchart.md")

    def test_report_draft_starts_none(self) -> None:
        draft = new_report_draft()
        self.assertIsNone(draft["status"])


if __name__ == "__main__":
    unittest.main()
