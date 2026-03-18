# MODIFIED: Updated writer assertions for prose-only output and evidence_references state.
from __future__ import annotations

import unittest
from unittest.mock import patch

from agents.preprocessing.query_expansion import expand
from agents.preprocessing.bias_mitigation import mitigate
from agents.preprocessing.router import route
from agents.common.quality_check import check
from agents.common.content_writer import write
from agents.common.content_evaluator import evaluate
from agents.market.agent import run as run_market
from agents.lges.agent import run as run_lges
from agents.catl.agent import run as run_catl
from agents.parallel_runner import execute_parallel
from schemas import new_company_state, new_global_state


class TestPhase2To4(unittest.TestCase):
    def test_query_expansion_and_global_state_update(self) -> None:
        gs = new_global_state("r1")
        out = expand("LGES CATL", gs)
        self.assertGreater(len(out), 1)
        self.assertEqual(gs["user_query"], "LGES CATL")
        with self.assertRaises(ValueError):
            expand("   ")

    def test_bias_and_router_updates(self) -> None:
        gs = new_global_state("r1")
        bq = mitigate(["q"], gs)
        self.assertTrue(any("긍정" in q for q in bq))
        self.assertTrue(any("부정" in q for q in bq))
        rt = route(bq, gs)
        self.assertTrue(all(k in rt for k in ("catl", "lges", "market")))

    def test_quality_writer_evaluator(self) -> None:
        ok, _ = check([])
        self.assertFalse(ok)
        evidence = [{
            "source_type": "web", "source_url": "u", "published_at": "2026-01-01", "retrieved_at": "2026-01-01",
            "source_name": "s", "domain": "market", "title": "t", "excerpt": "e", "year": "2026",
        }]
        ok, _ = check(evidence)
        self.assertTrue(ok)
        d = write([], "x")
        self.assertIn("데이터 없음", d)
        d2 = write(evidence, "x", company_state=new_company_state(), run_id="r1")
        self.assertNotIn("\n- ", d2)
        st = new_company_state()
        approved, _ = evaluate("", "x", st)
        self.assertFalse(approved)
        st["evidence_references"] = [{"source": "s", "page": "1", "year": "2026"}]
        approved, _ = evaluate("리스크 요인을 검토한 문단이다.", "x", st)
        self.assertTrue(approved)
        self.assertTrue(st["approved"])

    def test_market_order_and_loop(self) -> None:
        gs = new_global_state("r1")
        routes = {"market": "m", "lges": "l", "catl": "c"}
        calls: list[str] = []

        def s(*args, **kwargs):
            calls.append("web")
            return [{"source_type": "web", "source_url": "u", "published_at": "2026-01-01", "retrieved_at": "2026-01-01", "source_name": "s", "domain": "market", "title": "t", "excerpt": "e", "year": "2026"}]

        with patch("agents.market.agent.search", side_effect=s), \
             patch("agents.market.agent.query", side_effect=lambda *a, **k: calls.append("paper") or []), \
             patch("agents.market.agent.quality_check", side_effect=lambda ev: (calls.append("quality") or True, "ok")), \
             patch("agents.market.agent.write", side_effect=lambda *a, **k: calls.append("write") or "- 반대 근거 [s, 2026]"), \
             patch("agents.market.agent.evaluate", side_effect=lambda *a, **k: (calls.append("eval") or True, "")):
            run_market(routes, gs)
        self.assertEqual(calls[:5], ["web", "paper", "quality", "write", "eval"])

    def test_agent_scope_and_state_isolation(self) -> None:
        gs = new_global_state("r1")
        routes = {"market": "m", "lges": "l", "catl": "c"}
        lges_state = run_lges(routes, gs)
        catl_state = run_catl(routes, gs)
        self.assertTrue(lges_state["draft"])
        self.assertTrue(catl_state["draft"])

    def test_parallel_wrapper_resilience(self) -> None:
        ok_state = new_company_state()
        ok_state["approved"] = True

        def bad():
            raise RuntimeError("x")

        m, l, c = execute_parallel(lambda: ok_state, bad, lambda: ok_state)
        self.assertTrue(m["approved"])
        self.assertFalse(l["approved"])
        self.assertTrue(c["approved"])


if __name__ == "__main__":
    unittest.main()
