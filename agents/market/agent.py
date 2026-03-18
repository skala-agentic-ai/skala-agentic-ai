# MODIFIED: Pass company_state/run_id into content writer for separate evidence_references capture.
from __future__ import annotations

from constants import MAX_LOOP
from schemas import CompanyState, GlobalState, new_company_state
from retrieval.web_search import search
from retrieval.vector_store import query
from agents.common.quality_check import check as quality_check
from agents.common.content_writer import write
from agents.common.content_evaluator import evaluate


def run(task_routes: dict[str, str], global_state: GlobalState) -> CompanyState:
    state = new_company_state()
    scope = "1. 시장 배경"
    for _ in range(MAX_LOOP):
        web_results = search([task_routes["market"]])
        paper_results = query("market", [task_routes["market"]])
        evidence_pool = paper_results + web_results
        ok, reason = quality_check(evidence_pool)
        if not ok:
            state["retry_instruction"] = reason
            continue
        state["evidence_pool"] = evidence_pool
        draft = write(
            evidence_pool,
            scope,
            company_state=state,
            run_id=global_state["run_id"],
            agent_name="market",
        )
        state["draft"] = draft
        approved, instruction = evaluate(draft, scope, company_state=state)
        if approved:
            return state
        state["retry_instruction"] = instruction
    state["retry_instruction"] = state.get("retry_instruction", "") or "max loop exceeded"
    return state
