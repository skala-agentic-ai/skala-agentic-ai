# MODIFIED: 섹션 분리(draft_sections) 저장 및 참조 메타데이터 강화
from __future__ import annotations

import json
import logging
import re
from typing import Callable

from agents.common.prompts import PROMPT_SECTION_WRITER
from agents.report_writer.prompts import PROMPT_CATL_ANALYSIS, PROMPT_LGES_ANALYSIS
from schemas import CompanyState, SourceDoc


ResponseType = dict | str
MAX_EVIDENCE_CHARS = 6000
MIN_SECTION_CHARS = 500


def write(
    evidence_pool: list[SourceDoc],
    section_scope: str,
    company_state: CompanyState | None = None,
    run_id: str = "unknown",
    agent_name: str = "unknown",
    llm_call: Callable[[str, str, str], ResponseType] | None = None,
) -> str:
    logger = logging.getLogger(f"pipeline.{run_id}")
    if not evidence_pool:
        if company_state is not None:
            company_state["evidence_references"] = []
        if agent_name in {"lges", "catl"}:
            return "섹션 생성 실패 (사유: evidence_pool 비어있음)"
        return "데이터 없음 (사유: evidence_pool 비어 있음)"

    is_company_section = agent_name in {"lges", "catl"}
    if is_company_section:
        evidence_text = _serialize_evidence(evidence_pool)
        prompt = PROMPT_LGES_ANALYSIS if agent_name == "lges" else PROMPT_CATL_ANALYSIS
        user_payload = prompt.replace("{evidence}", evidence_text)
    else:
        evidence_text = _build_user_payload(evidence_pool, section_scope)
        prompt = PROMPT_SECTION_WRITER
        user_payload = evidence_text

    caller = llm_call or _default_llm_call

    try:
        raw = _invoke_llm(caller, prompt, user_payload, run_id, max_tokens=2000)
        result = _to_dict(raw)
        sections = _normalize_sections(result.get("sections", {}), agent_name)
        if is_company_section and sections:
            prose = _clean_prose(_compose_flat_from_sections(sections))
        else:
            prose = _clean_prose(str(result.get("prose", "")))
            if is_company_section:
                sections = _split_flat_prose_to_sections(prose, agent_name)
        references = _normalize_references(result.get("references", []))
        if is_company_section:
            source_refs = [_source_doc_to_ref(doc) for doc in evidence_pool]
            references = _merge_references(references, source_refs)
        if is_company_section and not _is_sufficient_length(prose):
            logger.warning(
                {
                    "event": "draft_too_short",
                    "run_id": run_id,
                    "agent": agent_name,
                    "length": len(prose),
                    "minimum": MIN_SECTION_CHARS,
                }
            )
            prose = _retry_with_length_instruction(
                evidence_text=evidence_text,
                agent_name=agent_name,
                llm_call=caller,
                run_id=run_id,
            )
        if company_state is not None:
            company_state["evidence_references"] = references
            if is_company_section:
                company_state["draft_sections"] = sections
        if not prose:
            raise ValueError("empty prose in LLM response")
        return prose
    except Exception as exc:
        logging.getLogger(f"pipeline.{run_id}").exception(
            "run_id=%s agent=%s section=%s content_write_failed: %s",
            run_id,
            agent_name,
            section_scope,
            exc,
        )
        if company_state is not None:
            company_state["evidence_references"] = []
            if is_company_section:
                company_state["draft_sections"] = {}
        return f"섹션 생성 실패 (사유: {exc})"


def _build_user_payload(evidence_pool: list[SourceDoc], section_scope: str) -> str:
    lines = ["[근거 자료]"]
    for doc in evidence_pool[:10]:
        page = _extract_page(doc)
        lines.append(
            f"- source={doc['source_name']} | page=p.{page} | year={doc['year']} | excerpt={doc['excerpt'][:220]}"
        )
    lines.append("")
    lines.append("[작성 범위]")
    lines.append(section_scope)
    return "\n".join(lines)


def _serialize_evidence(docs: list[SourceDoc]) -> str:
    chunks: list[str] = []
    total = 0
    for i, doc in enumerate(docs):
        content = str(doc.get("content", "")) if isinstance(doc, dict) else ""
        if not content:
            content = str(doc.get("excerpt", "")) if isinstance(doc, dict) else ""
        entry = (
            f"[근거 {i + 1}]\n"
            f"출처: {doc.get('source_url', '')}\n"
            f"발행일: {doc.get('published_at') or '미상'}\n"
            f"내용: {content}\n"
        )
        if total + len(entry) > MAX_EVIDENCE_CHARS:
            break
        chunks.append(entry)
        total += len(entry)
    return "\n".join(chunks)


def _default_llm_call(system_prompt: str, user_payload: str, run_id: str) -> ResponseType:
    del system_prompt, run_id
    if "[근거 1]" in user_payload and ("LG에너지솔루션" in user_payload or "CATL" in user_payload):
        refs, facts = _extract_evidence_blocks(user_payload)
        sections = _build_company_sections(user_payload, facts)
        return {"sections": sections, "references": refs}

    evidence_lines = [ln for ln in user_payload.splitlines() if ln.startswith("- source=")]
    refs = []
    facts = []
    for ln in evidence_lines[:6]:
        source = _extract_attr(ln, "source")
        page = _extract_attr(ln, "page")
        year = _extract_attr(ln, "year")
        excerpt = _extract_attr(ln, "excerpt")
        refs.append({"source": source or "문서명 미상", "page": page or "p.?", "year": year or "2026"})
        facts.append(_paraphrase_fact(excerpt))

    p1 = _ensure_min_sentences(
        "본 섹션은 수집된 근거를 교차 비교해 핵심 시장 신호를 구조화했다. "
        + " ".join(facts[:2])
        + " 정책 변수와 수요 전환 속도는 동일 기간에 동시 관리되어야 하며, 단일 지표만으로 전략을 판단하면 왜곡 위험이 커진다."
    )
    p2 = _ensure_min_sentences(
        "기업 실행 관점에서는 공급망 안정성과 제품 포트폴리오 조정 능력이 성과 편차를 좌우한다. "
        + " ".join(facts[2:4])
        + " 따라서 리스크 대응 체계는 비용, 지역, 기술 세 축을 함께 관리하는 방식으로 설계되어야 한다."
    )

    return {"prose": f"{p1}\n\n{p2}", "references": refs}


def _paraphrase_fact(excerpt: str) -> str:
    text = re.sub(r"\s+", " ", excerpt).strip()
    text = re.sub(r"\[[^\]]+\]", "", text)
    if not text:
        return "자료는 시장 변동성과 정책 영향이 동시에 확대되는 흐름을 시사한다."
    signals = []
    if "ESS" in text:
        signals.append("ESS 확장")
    if "북미" in text or "IRA" in text:
        signals.append("북미 정책 변수")
    if "원가" in text or "수익" in text:
        signals.append("원가·수익성 압력")
    if "공급망" in text:
        signals.append("공급망 재편")
    if "수요" in text:
        signals.append("수요 전환")
    if not signals:
        signals.append("핵심 사업지표 변화")
    return f"자료는 {'·'.join(dict.fromkeys(signals))}가 동시에 작동하는 환경임을 보여준다."


def _extract_attr(line: str, key: str) -> str:
    token = f"{key}="
    if token not in line:
        return ""
    segment = line.split(token, 1)[1]
    if " | " in segment:
        segment = segment.split(" | ", 1)[0]
    return segment.strip()


def _extract_page(doc: SourceDoc) -> str:
    if "#page=" in doc["source_url"]:
        return doc["source_url"].split("#page=", 1)[1]
    return "?"


def _to_dict(raw: ResponseType) -> dict:
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


def _normalize_references(raw_refs: object) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    if not isinstance(raw_refs, list):
        return refs
    for item in raw_refs:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source", "문서명 미상")).strip()
        source_url = str(item.get("source_url", "")).strip()
        source_type = str(item.get("source_type", "pdf"))
        if source_url.startswith("http"):
            source_type = "web"
        if source.startswith("http"):
            source_url = source
            source_type = "web"
        if source in {"[]", ""} and not item.get("source_url") and not item.get("title"):
            continue
        refs.append(
            {
                "source": source,
                "page": str(item.get("page", "p.?")),
                "year": str(item.get("year", "2026")),
                "source_type": source_type,
                "source_url": source_url,
                "title": str(item.get("title", "")),
            }
        )
    return refs


def _extract_evidence_blocks(evidence_text: str) -> tuple[list[dict[str, str]], list[str]]:
    refs: list[dict[str, str]] = []
    facts: list[str] = []
    blocks = re.split(r"\[근거 \d+\]\n", evidence_text)
    for block in blocks:
        chunk = block.strip()
        if not chunk:
            continue
        source_match = re.search(r"출처:\s*(.+)", chunk)
        date_match = re.search(r"발행일:\s*(.+)", chunk)
        content_match = re.search(r"내용:\s*(.+)", chunk, flags=re.DOTALL)
        source = source_match.group(1).strip() if source_match else "문서명 미상"
        published = date_match.group(1).strip() if date_match else "2026-01-01"
        content = content_match.group(1).strip() if content_match else ""
        year = _extract_year_from_text(published)
        is_web = source.startswith("http")
        page = "" if is_web else _extract_page_from_source(source)
        refs.append(
            {
                "source": "" if is_web else _extract_file_name(source),
                "source_type": "web" if is_web else "pdf",
                "source_url": source if is_web else "",
                "title": "",
                "page": page,
                "year": year,
            }
        )
        if content:
            facts.append(_paraphrase_fact(content))
    return refs, facts


def _build_company_sections(user_payload: str, facts: list[str]) -> dict[str, str]:
    if "2.1~2.4 LG에너지솔루션 전략 분석" in user_payload:
        k1, k2, k3, k4 = "2.1", "2.2", "2.3", "2.4"
        h1, h2, h3, h4 = "핵심 전략 방향", "수익성 및 KPI", "긍정 근거", "반대 근거 / 리스크"
    else:
        k1, k2, k3, k4 = "3.1", "3.2", "3.3", "3.4"
        h1, h2, h3, h4 = "핵심 전략 방향", "수익성 및 KPI", "긍정 근거", "반대 근거 / 리스크"
    f = facts + ["근거 자료는 수요 전환기 대응과 공급망 안정화가 동시에 요구된다는 점을 보여준다."] * 8
    s1 = _ensure_min_sentences(
        f"해당 기업은 시장 수요 변동성과 정책 환경 변화를 동시에 고려해 {h1}을 재설계하고 있다. "
        f"{f[0]} {f[1]} 실행 우선순위는 단기 방어와 중기 성장의 균형에 맞춰 조정되는 양상이다."
    )
    s2 = _ensure_min_sentences(
        f"수익성은 원가 구조와 가동률, 그리고 제품 믹스의 결합으로 결정되며 {h2} 관점에서 해석되어야 한다. "
        f"{f[2]} {f[3]} KPI 해석은 단일 지표가 아니라 정책 변수와 수요 회복 속도를 함께 반영해야 한다."
    )
    s3 = _ensure_min_sentences(
        f"긍정 요인은 기술 포트폴리오와 고객 기반 확장, 그리고 실행 체계의 정합성에서 확인된다. "
        f"{f[4]} {f[5]} 특히 공급망 대응 속도와 파트너십 운영 역량은 성장 동인을 강화하는 핵심 축으로 작동한다."
    )
    s4 = _ensure_min_sentences(
        f"반대 근거는 수요 둔화 장기화, 원가 압력 확대, 규제 불확실성에서 도출되며 {h4} 관점에서 관리되어야 한다. "
        f"{f[6]} {f[7]} 따라서 리스크 관리 체계는 투자 우선순위와 운영 지표를 연동해 선제적으로 조정되어야 한다."
    )
    return {k1: s1, k2: s2, k3: s3, k4: s4}


def _clean_prose(text: str) -> str:
    text = re.sub(r"\[[^\]]+,\s*\d{4}\]", "", text)
    text = re.sub(r"^\s*[-*]\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_sufficient_length(text: str) -> bool:
    return len(text.replace(" ", "")) >= MIN_SECTION_CHARS


def _retry_with_length_instruction(
    evidence_text: str,
    agent_name: str,
    llm_call: Callable[..., ResponseType],
    run_id: str,
) -> str:
    logger = logging.getLogger(f"pipeline.{run_id}")
    retry_prompt = (
        f"이전 응답이 {MIN_SECTION_CHARS}자 미만이었습니다. "
        f"아래 근거 자료를 더 깊이 분석하여 반드시 {MIN_SECTION_CHARS}자 이상의 줄글로 다시 작성하십시오. "
        "항목별(핵심전략/수익성KPI/긍정근거/리스크) 구분을 유지하십시오.\n\n"
        f"[근거 자료]\n{evidence_text}"
    )
    try:
        response = _invoke_llm(
            llm_call,
            "배터리 산업 전략 분석 전문가로서 지시에 따라 작성하십시오.",
            retry_prompt,
            run_id,
            max_tokens=2000,
        )
        result = _to_dict(response)
        prose = _clean_prose(_parse_prose(result))
        if prose and _is_sufficient_length(prose):
            return prose
        return "섹션 생성 실패 (재시도 후에도 분량 미달)"
    except Exception as exc:
        logger.error(
            {
                "event": "draft_retry_failed",
                "run_id": run_id,
                "agent": agent_name,
                "error": str(exc),
            }
        )
        return f"섹션 생성 실패 (사유: {exc})"


def _parse_prose(response: dict) -> str:
    sections = response.get("sections")
    if isinstance(sections, dict):
        keys = sorted([k for k in sections.keys() if isinstance(k, str)])
        if keys:
            return _compose_flat_from_sections({k: str(sections.get(k, "")) for k in keys})
    return str(response.get("prose", ""))


def _invoke_llm(
    llm_call: Callable[..., ResponseType],
    system_prompt: str,
    user_payload: str,
    run_id: str,
    max_tokens: int,
) -> ResponseType:
    try:
        return llm_call(system_prompt, user_payload, run_id, max_tokens=max_tokens)
    except TypeError:
        return llm_call(system_prompt, user_payload, run_id)


def _ensure_min_sentences(paragraph: str, minimum: int = 4) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
    while len(sentences) < minimum:
        sentences.append("근거 자료의 공통 신호를 기준으로 해석의 일관성을 유지했다.")
    return " ".join(sentences[:6])


def _extract_year_from_text(text: str) -> str:
    match = re.search(r"(20\d{2})", text)
    return match.group(1) if match else "2026"


def _extract_file_name(source_url: str) -> str:
    cleaned = source_url.split("#", 1)[0].strip()
    if "/" in cleaned:
        return cleaned.rsplit("/", 1)[-1] or cleaned
    return cleaned


def _extract_page_from_source(source_url: str) -> str:
    if "#page=" in source_url:
        return f"p.{source_url.split('#page=', 1)[1]}"
    return "p.?"


def _normalize_sections(raw_sections: object, agent_name: str) -> dict[str, str]:
    if not isinstance(raw_sections, dict):
        return {}
    keys = ["2.1", "2.2", "2.3", "2.4"] if agent_name == "lges" else ["3.1", "3.2", "3.3", "3.4"]
    out: dict[str, str] = {}
    for key in keys:
        value = raw_sections.get(key, "")
        if value is None:
            value = ""
        out[key] = _clean_prose(str(value))
    return out


def _compose_flat_from_sections(sections: dict[str, str]) -> str:
    lines: list[str] = []
    for key in sorted(sections.keys()):
        body = str(sections.get(key, "")).strip()
        if not body:
            continue
        lines.append(f"{key} {body}")
    return "\n\n".join(lines)


def _split_flat_prose_to_sections(flat: str, agent_name: str) -> dict[str, str]:
    keys = ["2.1", "2.2", "2.3", "2.4"] if agent_name == "lges" else ["3.1", "3.2", "3.3", "3.4"]
    result: dict[str, str] = {}
    pattern = "|".join(re.escape(k) for k in keys)
    parts = re.split(f"({pattern})", flat)
    current_key: str | None = None
    for part in parts:
        stripped = part.strip()
        if stripped in keys:
            current_key = stripped
            continue
        if current_key and stripped:
            result[current_key] = (result.get(current_key, "") + " " + stripped).strip()
    return result


def _source_doc_to_ref(doc: SourceDoc) -> dict[str, str]:
    source_url = str(doc.get("source_url", ""))
    source_name = str(doc.get("source_name", ""))
    title = str(doc.get("title", ""))
    source_type = str(doc.get("source_type", "pdf"))
    source = _extract_file_name(source_name or source_url) if source_type == "pdf" else ""
    page = _extract_page_from_source(source_url) if source_type == "pdf" else ""
    published = str(doc.get("published_at", ""))
    year = _extract_year_from_text(published) if published else str(doc.get("year", "2026"))
    return {
        "source": source,
        "source_type": source_type,
        "source_url": source_url,
        "title": title,
        "page": page,
        "year": year or "2026",
    }


def _merge_references(primary: list[dict[str, str]], fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in primary + fallback:
        source = str(item.get("source", ""))
        url = str(item.get("source_url", ""))
        title = str(item.get("title", ""))
        if not source and not url and not title:
            continue
        key = (source, url, title)
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged
