# MODIFIED: SUMMARY truncation 방지(max_tokens/완결성 검증) 추가
from __future__ import annotations

import json
import logging
import re
from typing import Callable

from agents.report_writer.prompts import PROMPT_SUMMARY


ResponseType = dict | str
LOGGER = logging.getLogger(__name__)


def generate(
    lges_analysis: str | object,
    catl_analysis: str | object = "",
    comparison_matrix: str | object = "",
    market_background: str | object = "",
    run_id: str = "unknown",
    llm_call: Callable[[str, str, str], ResponseType] | None = None,
) -> str:
    # Backward compatibility for legacy call shape:
    # generate(comparison_matrix_dict, swot_dict, implications_text, run_id?)
    if isinstance(lges_analysis, dict) and isinstance(catl_analysis, dict):
        legacy_comparison = json.dumps(lges_analysis, ensure_ascii=False)
        legacy_swot = json.dumps(catl_analysis, ensure_ascii=False)
        legacy_imp = str(comparison_matrix)
        lges_analysis = f"{legacy_comparison}\n{legacy_swot}"
        catl_analysis = legacy_imp
        comparison_matrix = legacy_comparison
        market_background = str(market_background) if market_background else ""

    caller = llm_call or _default_llm_call
    user_payload = (
        f"[LGES 분석]\n{str(lges_analysis)}\n\n"
        f"[CATL 분석]\n{str(catl_analysis)}\n\n"
        f"[핵심 전략 비교]\n{str(comparison_matrix)}\n\n"
        f"[시장 배경]\n{str(market_background)}"
    )

    try:
        raw = _invoke_llm(caller, PROMPT_SUMMARY, user_payload, run_id, max_tokens=1000)
        data = raw if isinstance(raw, dict) else json.loads(raw)
        bullets = data.get("bullets")
        if not isinstance(bullets, list) or len(bullets) < 4:
            raise ValueError("bullets list missing or < 4")
        cleaned: list[str] = []
        for idx, bullet in enumerate(bullets[:4]):
            text = _strip_citations(str(bullet)).strip()
            text = text[2:].strip() if text.startswith("- ") else text
            if text and not _is_complete_sentence(text):
                LOGGER.warning(
                    {
                        "event": "summary_bullet_truncated",
                        "run_id": run_id,
                        "bullet_index": idx,
                        "bullet_preview": text[:80],
                    }
                )
                text = _complete_bullet(text, caller, run_id)
            if text:
                cleaned.append(f"- {text}")
        if len(cleaned) < 4:
            raise ValueError("cleaned bullets < 4")
        return "\n".join(cleaned)
    except Exception as exc:
        logging.getLogger(f"pipeline.{run_id}").exception(
            "run_id=%s summary_generation_failed: %s", run_id, exc
        )
        return f"SUMMARY 생성 실패 (사유: {exc})"


def _default_llm_call(system_prompt: str, user_payload: str, run_id: str) -> ResponseType:
    del system_prompt, run_id
    # Deterministic local fallback that follows required 4-topic structure.
    bg = "캐즘" if "캐즘" in user_payload else "수요"
    lges_kw = "북미" if "북미" in user_payload else "BaaS"
    catl_kw = "인프라" if "인프라" in user_payload else "도메인"
    comp_kw = "경쟁" if "경쟁" in user_payload else "로드맵"
    return {
        "bullets": [
            f"전기차 캐즘 대응: {bg} 둔화 국면에서 LGES와 CATL은 생산·포트폴리오 조정 속도에 차이를 보이며 대응한다. LGES는 수익성 방어 중심, CATL은 시장 확장 중심으로 실행 우선순위를 두는 경향이 확인된다.",
            f"LGES 전략: {lges_kw} 거점 중심 운영과 BaaS 확장은 고객 락인과 수요 탄력성 확보를 동시에 노리는 구조다. 이는 변동성 구간에서 현금흐름 안정성과 중장기 계약 기반 확대에 유리하게 작용할 수 있다.",
            f"CATL 전략: 올 도메인 확장과 충전·스왑 {catl_kw} 표준화 전략은 생태계 지배력 강화에 초점을 둔다. 제품-서비스-인프라를 결합한 접근은 규모의 경제를 유지하며 신규 지역 진입 장벽을 낮출 가능성이 높다.",
            f"경쟁력 진단: {comp_kw} 구도는 수익성 지표, 기술 로드맵, 공급망 안정성의 결합에서 결정된다. 중기 경쟁우위는 단일 기술이 아니라 실행 일관성과 지역 분산 전략을 얼마나 정교하게 운영하느냐에 달려 있다.",
        ]
    }


def _strip_citations(text: str) -> str:
    return re.sub(r"\[.+?,\s*\d{4}\]", "", text)


def _is_complete_sentence(text: str) -> bool:
    stripped = text.strip()
    return len(stripped) > 0 and stripped[-1] in ("다", ".", "?", "!")


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


def _complete_bullet(
    partial: str,
    llm_call: Callable[..., ResponseType],
    run_id: str,
) -> str:
    try:
        response = _invoke_llm(
            llm_call,
            (
                "아래 문장을 자연스럽게 완성하십시오. "
                "한 문장으로 끝내며 마침표로 마무리하십시오. "
                "응답은 완성된 전체 문장만 반환하십시오."
            ),
            partial,
            run_id,
            max_tokens=300,
        )
        result = str(response).strip()
        if result and result[-1] not in ("다", ".", "?", "!"):
            result += "."
        return result
    except Exception as exc:
        LOGGER.error(
            {
                "event": "summary_bullet_completion_failed",
                "run_id": run_id,
                "error": str(exc),
            }
        )
        return partial.rstrip() + "."
