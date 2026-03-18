# MODIFIED: 섹션 2/3 draft 할당 길이 로깅 추가
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from constants import MAX_ALLOWED_FAILURES
from schemas import CompanyState, ReportDraft, new_report_draft
from agents.report_writer.comparison_matrix import generate as gen_matrix
from agents.report_writer.swot import generate as gen_swot
from agents.report_writer.implications import generate as gen_implications
from agents.report_writer.summary import generate as gen_summary
from agents.report_writer.reference_compiler import compile as compile_refs


class ReportWriterError(RuntimeError):
    pass


def run(
    global_findings: str,
    market_state: CompanyState,
    lges_state: CompanyState,
    catl_state: CompanyState,
    run_id: str = "unknown",
) -> ReportDraft:
    draft = new_report_draft()
    failures = 0

    parsed_market = _extract_block(global_findings, "<<<MARKET>>>", "<<<END_MARKET>>>", "")
    parsed_lges = _extract_block(global_findings, "<<<LGES>>>", "<<<END_LGES>>>", "")
    parsed_catl = _extract_block(global_findings, "<<<CATL>>>", "<<<END_CATL>>>", "")

    lges_draft = lges_state.get("draft", "") or parsed_lges
    catl_draft = catl_state.get("draft", "") or parsed_catl
    lges_kpi = lges_state.get("kpi_snapshot", {})
    catl_kpi = catl_state.get("kpi_snapshot", {})

    # fork1
    with ThreadPoolExecutor(max_workers=3) as ex:
        f_matrix = ex.submit(gen_matrix, lges_draft, catl_draft, lges_kpi, catl_kpi, run_id)
        f_swot = ex.submit(gen_swot, lges_draft, catl_draft, global_findings, run_id)

        implications_inputs = {
            "lges_analysis": lges_draft,
            "catl_analysis": catl_draft,
            "comparison_matrix": str(draft.get("comparison_matrix", {})),
            "swot": str(draft.get("swot", {})),
            "market_background": market_state.get("draft", "") or parsed_market,
        }
        for field_name, value in implications_inputs.items():
            if not str(value).strip():
                logging.getLogger(f"pipeline.{run_id}").warning(
                    "run_id=%s implications_input_empty: %s", run_id, field_name
                )

        f_imp = ex.submit(
            gen_implications,
            implications_inputs["lges_analysis"],
            implications_inputs["catl_analysis"],
            implications_inputs["comparison_matrix"],
            implications_inputs["swot"],
            implications_inputs["market_background"],
            run_id,
        )

        try:
            draft["comparison_matrix"] = f_matrix.result()
        except Exception as exc:
            failures += 1
            draft["comparison_matrix"] = {"error": f"섹션 생성 실패 (사유: {exc})"}
        try:
            draft["swot"] = f_swot.result()
        except Exception as exc:
            failures += 1
            draft["swot"] = {"error": f"섹션 생성 실패 (사유: {exc})"}
        try:
            draft["implications"] = f_imp.result()
        except Exception as exc:
            failures += 1
            draft["implications"] = f"섹션 생성 실패 (사유: {exc})"

    draft["market_background"] = market_state.get("draft", "") or parsed_market or "시장 자료 요약"
    draft["lges_analysis"] = lges_draft or "LGES 자료 요약"
    draft["catl_analysis"] = catl_draft or "CATL 자료 요약"
    logger = logging.getLogger(f"pipeline.{run_id}")
    logger.info(
        {
            "event": "report_draft_section_assigned",
            "run_id": run_id,
            "section": "lges_analysis",
            "length": len(draft["lges_analysis"]),
        }
    )
    logger.info(
        {
            "event": "report_draft_section_assigned",
            "run_id": run_id,
            "section": "catl_analysis",
            "length": len(draft["catl_analysis"]),
        }
    )

    # fork2 after join1
    with ThreadPoolExecutor(max_workers=2) as ex:
        summary_inputs = {
            "lges_analysis": draft.get("lges_analysis", ""),
            "catl_analysis": draft.get("catl_analysis", ""),
            "comparison_matrix": str(draft.get("comparison_matrix", {})),
            "market_background": draft.get("market_background", ""),
        }
        for field_name, value in summary_inputs.items():
            if not str(value).strip():
                logging.getLogger(f"pipeline.{run_id}").warning(
                    "run_id=%s summary_input_empty: %s", run_id, field_name
                )

        f_summary = ex.submit(
            gen_summary,
            summary_inputs["lges_analysis"],
            summary_inputs["catl_analysis"],
            summary_inputs["comparison_matrix"],
            summary_inputs["market_background"],
            run_id,
        )
        f_ref = ex.submit(compile_refs, [market_state, lges_state, catl_state])
        try:
            draft["summary"] = f_summary.result()
        except Exception as exc:
            failures += 1
            draft["summary"] = f"섹션 생성 실패 (사유: {exc})"
        try:
            draft["reference"] = f_ref.result()
        except Exception as exc:
            failures += 1
            draft["reference"] = [{"source": "error", "page": "?", "year": "0000", "reason": str(exc)}]

    if failures > MAX_ALLOWED_FAILURES:
        raise ReportWriterError("MaxAllowedFailures exceeded")

    draft["status"] = "pending_validation"
    return draft


def _extract_block(global_findings: str, start: str, end: str, fallback: str) -> str:
    if start not in global_findings or end not in global_findings:
        return fallback
    block = global_findings.split(start, 1)[1].split(end, 1)[0].strip()
    return block if block else fallback
