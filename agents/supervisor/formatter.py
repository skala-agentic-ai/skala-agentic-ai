# MODIFIED: 섹션 2/3 소제목 렌더링 및 REFERENCE 정규화 연결
from __future__ import annotations

import re
from datetime import datetime, timezone

from agents.report_writer.reference_compiler import render_reference_section
from schemas import ReportDraft


class FormattingError(RuntimeError):
    pass


CITATION_PATTERN = re.compile(r"\[.+?,\s*\d{4}\]")
LGES_SUBSECTION_TITLES = {
    "2.1": "핵심 전략 방향",
    "2.2": "수익성 및 KPI",
    "2.3": "긍정 근거",
    "2.4": "반대 근거 / 리스크",
}
CATL_SUBSECTION_TITLES = {
    "3.1": "핵심 전략 방향",
    "3.2": "수익성 및 KPI",
    "3.3": "긍정 근거",
    "3.4": "반대 근거 / 리스크",
}


def strip_citations(text: str) -> str:
    return CITATION_PATTERN.sub("", text).strip()


def format(report_draft: ReportDraft, run_id: str | None = None) -> str:
    if report_draft is None:
        raise FormattingError("report_draft is None")

    analysis_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    del run_id
    title_block = (
        "# 배터리 시장 전략 분석 보고서\n\n"
        f"> **분석 기준일:** {analysis_date}\n\n"
        "---\n\n"
    )

    sections = [
        "## SUMMARY\n\n" + strip_citations(report_draft["summary"]),
        "# 1. 시장 배경\n" + _format_prose(report_draft["market_background"]),
        _render_company_section_from_flat("2", "LG에너지솔루션 전략 분석", report_draft["lges_analysis"], LGES_SUBSECTION_TITLES),
        _render_company_section_from_flat("3", "CATL 전략 분석", report_draft["catl_analysis"], CATL_SUBSECTION_TITLES),
        "# 4. 핵심 전략 비교\n" + _format_matrix(report_draft["comparison_matrix"]),
        "# 5. SWOT 분석\n" + _format_swot(report_draft["swot"]),
        "## 6. 종합 시사점\n\n" + strip_citations(report_draft["implications"]),
        "## REFERENCE\n" + _format_reference(report_draft["reference"]),
    ]
    return title_block + "\n\n".join(sections)


def _format_prose(text: str) -> str:
    if not text.strip():
        return "데이터 없음"
    cleaned = strip_citations(text)
    lines = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        stripped = stripped.lstrip("- ")
        lines.append(stripped)
    body = "\n\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _format_matrix(matrix: dict) -> str:
    head = "|항목|LGES|CATL|\n|---|---|---|"
    rows = []
    for key, value in matrix.items():
        if isinstance(value, dict):
            rows.append(f"|{key}|{value.get('lges', '')}|{value.get('catl', '')}|")
        else:
            rows.append(f"|{key}|{value}|{value}|")
    return "\n".join([head] + rows)


def _safe_swot_cell(value: str | None) -> str:
    if value is None or not str(value).strip():
        return "데이터 없음"
    text = str(value).strip()
    if text.startswith("분석 실패") or text.startswith("분석 필요"):
        return f"⚠️ {text}"
    return text


def _format_swot(swot: dict) -> str:
    lges = swot.get("lges", {}) if isinstance(swot, dict) else {}
    catl = swot.get("catl", {}) if isinstance(swot, dict) else {}
    rows = [
        "| 구분 | LGES | CATL |",
        "|------|------|------|",
        f"| S (강점) | {_safe_swot_cell(lges.get('S'))} | {_safe_swot_cell(catl.get('S'))} |",
        f"| W (약점) | {_safe_swot_cell(lges.get('W'))} | {_safe_swot_cell(catl.get('W'))} |",
        f"| O (기회) | {_safe_swot_cell(lges.get('O'))} | {_safe_swot_cell(catl.get('O'))} |",
        f"| T (위협) | {_safe_swot_cell(lges.get('T'))} | {_safe_swot_cell(catl.get('T'))} |",
    ]
    return "\n".join(rows)


def _format_reference(refs: list[dict]) -> str:
    return render_reference_section(refs)


def render_company_section(
    section_num: str,
    section_title: str,
    draft_sections: dict[str, str],
    subsection_titles: dict[str, str],
) -> str:
    lines = [f"## {section_num}. {section_title}\n"]
    keys = sorted(subsection_titles.keys())
    for i, key in enumerate(keys):
        title = subsection_titles[key]
        body = draft_sections.get(key, "").strip() or "내용 없음"
        lines.append(f"### {key} {title}\n")
        lines.append(f"{body}\n")
        if i < len(keys) - 1:
            lines.append("---\n")
    return "\n".join(lines).strip()


def _render_company_section_from_flat(
    section_num: str,
    section_title: str,
    flat: str,
    subsection_titles: dict[str, str],
) -> str:
    keys = sorted(subsection_titles.keys())
    draft_sections = _split_flat_draft(flat, keys)
    return render_company_section(section_num, section_title, draft_sections, subsection_titles)


def _split_flat_draft(flat: str, keys: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    pattern = "|".join(re.escape(k) for k in keys)
    parts = re.split(f"({pattern})", flat or "")
    current_key: str | None = None
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part in keys:
            current_key = part
            continue
        if current_key:
            merged = (result.get(current_key, "") + " " + part).strip()
            result[current_key] = merged
    return result
