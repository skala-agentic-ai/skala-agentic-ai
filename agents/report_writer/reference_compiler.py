# MODIFIED: web/pdf 표시명 정규화 및 empty/중복 레퍼런스 필터링
from __future__ import annotations

import re
from urllib.parse import urlparse

from schemas import CompanyState


def format_reference_entry(ref: dict) -> str:
    source = str(ref.get("source", "")).strip()
    source_type = str(ref.get("source_type", "pdf")).strip() or "pdf"
    title = str(ref.get("title", "")).strip()
    url = str(ref.get("source_url", "")).strip()
    year = str(ref.get("year", "")).strip()

    if source_type == "web":
        display_name = _clean_web_display(title, url)
    else:
        display_name = _clean_pdf_display(source)

    if year:
        return f"- {display_name} ({year})"
    return f"- {display_name}"


def compile(company_states: list[CompanyState]) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    compiled: list[dict] = []
    for company_state in company_states:
        for ref in company_state.get("evidence_references", []):
            source = str(ref.get("source", "문서명 미상")).strip()
            source_type = str(ref.get("source_type", "pdf")).strip() or "pdf"
            source_url = str(ref.get("source_url", "")).strip()
            title = str(ref.get("title", "")).strip()
            page = str(ref.get("page", "")).strip()
            year = str(ref.get("year", "0000"))
            key = (source, page, source_url)
            if key in seen:
                continue
            seen.add(key)
            compiled.append(
                {
                    "source": source,
                    "page": page,
                    "year": year,
                    "source_type": source_type,
                    "source_url": source_url,
                    "title": title,
                }
            )
    return compiled


def _clean_web_display(title: str, url: str) -> str:
    if title and len(title) > 10 and not title.startswith("http"):
        return title
    if not url:
        return "출처 미상"
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    path_parts = [
        p
        for p in parsed.path.split("/")
        if p and not p.endswith(".html") and len(p) > 3
    ]
    if path_parts:
        return f"{domain} — {path_parts[0]}" if domain else path_parts[0]
    return domain if domain else url[:60]


def _clean_pdf_display(source: str) -> str:
    if not source:
        return "출처 미상"
    # Remove trailing page tokens like " p.1" from PDF names.
    return re.sub(r"\s+p\.\d+\s*$", "", source).strip()


def _filter_valid_refs(refs: list) -> list[dict]:
    if not refs or not isinstance(refs, list):
        return []
    valid: list[dict] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        source = str(ref.get("source", "")).strip()
        source_url = str(ref.get("source_url", "")).strip()
        title = str(ref.get("title", "")).strip()
        if source in {"[]", "", "문서명 미상"} and not source_url and not title:
            continue
        valid.append(ref)
    return valid


def render_reference_section(refs: list) -> str:
    valid_refs = _filter_valid_refs(refs)
    if not valid_refs:
        return "참고문헌 없음 (근거 수집 실패)"

    seen: set[str] = set()
    lines: list[str] = []
    for ref in valid_refs:
        display_line = format_reference_entry(ref)
        if display_line in seen:
            continue
        seen.add(display_line)
        lines.append(display_line)
    return "\n".join(lines)
