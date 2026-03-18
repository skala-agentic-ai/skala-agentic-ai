# MODIFIED: WriteContent 입력 증거 로그 추가 및 empty evidence 가드
from __future__ import annotations

import logging

from constants import MAX_LOOP
from schemas import CompanyState, GlobalState, new_company_state
from retrieval.web_search import search
from retrieval.vector_store import query
from agents.common.quality_check import check as quality_check
from agents.common.content_writer import write
from agents.common.content_evaluator import evaluate


def run(task_routes: dict[str, str], global_state: GlobalState) -> CompanyState:
    state = new_company_state()
    scope = "3.1~3.4 CATL 전략 분석"
    for _ in range(MAX_LOOP):
        web_results = search([task_routes["catl"]])
        paper_results = query("CATL", [task_routes["catl"]])
        evidence_pool = paper_results + web_results
        ok, reason = quality_check(evidence_pool)
        if not ok:
            state["retry_instruction"] = reason
            continue
        state["evidence_pool"] = evidence_pool
        logger = logging.getLogger(f"pipeline.{global_state['run_id']}")
        logger.info(
            {
                "event": "write_content_input",
                "run_id": global_state["run_id"],
                "agent": "catl",
                "evidence_count": len(evidence_pool),
                "evidence_total_chars": sum(
                    len(str(doc.get("content", "")) or str(doc.get("excerpt", "")))
                    for doc in evidence_pool
                ),
            }
        )
        if not evidence_pool:
            logger.error(
                {
                    "event": "evidence_pool_empty_at_write",
                    "run_id": global_state["run_id"],
                    "agent": "catl",
                }
            )
            state["draft"] = "섹션 생성 실패 (사유: evidence_pool 비어있음)"
            return state
        draft = write(
            evidence_pool,
            scope,
            company_state=state,
            run_id=global_state["run_id"],
            agent_name="catl",
        )
        state["draft"] = draft
        approved, instruction = evaluate(draft, scope, company_state=state)
        if approved:
            return state
        state["retry_instruction"] = instruction
    state["retry_instruction"] = state.get("retry_instruction", "") or "max loop exceeded"
    return state
