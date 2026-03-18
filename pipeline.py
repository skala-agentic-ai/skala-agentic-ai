# MODIFIED: Pass per-company states into report writer for swot/reference generation from evidence references.
from __future__ import annotations

import time
import uuid

from constants import MAX_LOOP, MAX_RETRY, PIPELINE_TIMEOUT
from runtime import get_logger
from schemas import CompanyState, GlobalState, ReportDraft, new_global_state
from retrieval.pdf_loader import load_pdfs_from_dir
from retrieval.vector_store import ingest
from agents.preprocessing.query_expansion import expand
from agents.preprocessing.bias_mitigation import mitigate
from agents.preprocessing.router import route
from agents.market.agent import run as run_market
from agents.lges.agent import run as run_lges
from agents.catl.agent import run as run_catl
from agents.parallel_runner import execute_parallel
from agents.supervisor.global_consistency import check as consistency_check
from agents.supervisor.quality_gate import judge as quality_judge
from agents.supervisor.final_synth import synthesize
from agents.report_writer.agent import run as run_report_writer
from agents.supervisor.final_validation import validate as final_validate
from agents.supervisor.formatter import format as format_report
from agents.supervisor.report_saver import save as save_report


def run_pipeline(user_query: str, run_id: str | None = None) -> GlobalState:
    run_id = run_id or uuid.uuid4().hex[:8]
    state = new_global_state(run_id)
    logger = get_logger(run_id)

    started = time.monotonic()

    def ensure_timeout() -> None:
        elapsed = time.monotonic() - started
        if elapsed > PIPELINE_TIMEOUT:
            raise TimeoutError("pipeline timeout")

    ingest("market", load_pdfs_from_dir("data/market", "market"))
    ingest("LGES", load_pdfs_from_dir("data/LGES", "LGES"))
    ingest("CATL", load_pdfs_from_dir("data/CATL", "CATL"))

    expanded = expand(user_query, state)
    bias_queries = mitigate(expanded, state)
    task_routes = route(bias_queries, state)

    loop = 0
    market_state: CompanyState
    lges_state: CompanyState
    catl_state: CompanyState
    while True:
        ensure_timeout()
        logger.info("agent execution loop=%s", loop)
        market_state, lges_state, catl_state = execute_parallel(
            lambda: run_market(task_routes, state),
            lambda: run_lges(task_routes, state),
            lambda: run_catl(task_routes, state),
        )
        if not (market_state["approved"] and lges_state["approved"] and catl_state["approved"]):
            loop += 1
            if loop >= MAX_LOOP:
                state["retry_instruction"] = "Force Exit: agent approval max loop exceeded"
                return state
            task_routes = route(bias_queries + ["retry"], state)
            continue

        consistency = consistency_check(market_state, lges_state, catl_state, state)
        passed, instruction = quality_judge(consistency)
        if passed:
            synthesize(market_state, lges_state, catl_state, state)
            break
        state["retry_instruction"] = instruction
        loop += 1
        if loop >= MAX_LOOP:
            state["retry_instruction"] = "Force Exit: supervisor review max loop exceeded"
            return state
        task_routes = route(bias_queries + [instruction], state)

    retry = 0
    report_draft: ReportDraft | None = None
    while True:
        ensure_timeout()
        report_draft = run_report_writer(
            state["global_findings"],
            market_state,
            lges_state,
            catl_state,
            run_id=run_id,
        )
        ok, _failed_gates = final_validate(report_draft)
        if ok:
            markdown = format_report(report_draft)
            state["final_report"] = markdown
            save_report(markdown, run_id, state)
            return state
        retry += 1
        if retry > MAX_RETRY:
            markdown = format_report(report_draft)
            markdown += "\n\n## 한계\n- 최종 검증 실패 상태로 저장됨"
            state["final_report"] = markdown
            save_report(markdown, run_id, state)
            return state
