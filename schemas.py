# MODIFIED: CompanyState에 draft_sections 추가
"""Typed schemas and runtime validators."""
from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict

from constants import ALLOWED_REPORT_STATUS


class ValidationError(ValueError):
    """Raised when runtime schema validation fails."""


class SourceDoc(TypedDict):
    source_type: str
    source_url: str
    published_at: str
    retrieved_at: str
    source_name: str
    domain: str
    title: str
    excerpt: str
    year: str


class GlobalState(TypedDict):
    run_id: str
    user_query: str
    bias_queries: list[str]
    task_routes: dict[str, str]
    macro_market_context: str
    global_findings: str
    comparison_matrix: dict[str, Any]
    consistency_report: str
    retry_instruction: str
    final_report: str
    report_path: str


class CompanyState(TypedDict):
    evidence_pool: list[SourceDoc]
    evidence_references: list[dict[str, str]]
    draft: str
    draft_sections: dict[str, str]
    pro_arguments: list[str]
    con_arguments: list[str]
    kpi_snapshot: dict[str, Any]
    swot_draft: dict[str, Any]
    quality_score: float
    approved: bool
    retry_instruction: str


class ReportDraft(TypedDict):
    summary: str
    market_background: str
    lges_analysis: str
    catl_analysis: str
    comparison_matrix: dict[str, Any]
    swot: dict[str, Any]
    implications: str
    reference: list[dict[str, Any]]
    status: NotRequired[Literal["pending_validation", "validated", "failed"] | None]


def new_global_state(run_id: str) -> GlobalState:
    return GlobalState(
        run_id=run_id,
        user_query="",
        bias_queries=[],
        task_routes={},
        macro_market_context="",
        global_findings="",
        comparison_matrix={},
        consistency_report="",
        retry_instruction="",
        final_report="",
        report_path="",
    )


def new_company_state() -> CompanyState:
    return CompanyState(
        evidence_pool=[],
        evidence_references=[],
        draft="",
        draft_sections={},
        pro_arguments=[],
        con_arguments=[],
        kpi_snapshot={},
        swot_draft={},
        quality_score=0.0,
        approved=False,
        retry_instruction="",
    )


def new_report_draft() -> ReportDraft:
    return ReportDraft(
        summary="",
        market_background="",
        lges_analysis="",
        catl_analysis="",
        comparison_matrix={},
        swot={},
        implications="",
        reference=[],
        status=None,
    )


def validate_required_fields(name: str, data: dict[str, Any], required: set[str]) -> None:
    missing = sorted(required - set(data.keys()))
    if missing:
        raise ValidationError(f"{name} missing fields: {', '.join(missing)}")


def validate_report_status(value: str | None) -> None:
    if value not in ALLOWED_REPORT_STATUS:
        raise ValidationError(f"invalid report status: {value}")


def validate_source_doc(doc: dict[str, Any]) -> SourceDoc:
    required = {
        "source_type",
        "source_url",
        "published_at",
        "retrieved_at",
        "source_name",
        "domain",
        "title",
        "excerpt",
        "year",
    }
    validate_required_fields("SourceDoc", doc, required)
    return SourceDoc(**doc)
