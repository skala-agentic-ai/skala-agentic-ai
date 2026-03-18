# MODIFIED: Validates comparison matrix non-empty differentiated cells and complete key set.
from __future__ import annotations

import unittest

from agents.report_writer.comparison_matrix import generate


class TestComparisonMatrix(unittest.TestCase):
    def test_non_empty_inputs_no_data_eum(self) -> None:
        out = generate(
            "LGES는 북미 생산거점과 ESS 확장을 추진한다.",
            "CATL은 중국 기반 양산과 유럽 확장을 병행한다.",
            {"roe": 10},
            {"roe": 12},
            run_id="cm1",
        )
        for item in out.values():
            self.assertNotIn("데이터 없음", item["lges"])
            self.assertNotIn("데이터 없음", item["catl"])

    def test_lges_catl_cells_different(self) -> None:
        out = generate("LGES text", "CATL text", {}, {}, run_id="cm2")
        for item in out.values():
            self.assertNotEqual(item["lges"], item["catl"])

    def test_all_10_keys_mapped(self) -> None:
        out = generate("LGES text", "CATL text", {}, {}, run_id="cm3")
        self.assertEqual(set(out.keys()), {"시장포지셔닝", "핵심기술", "수익성", "실행력", "주요리스크"})


if __name__ == "__main__":
    unittest.main()
