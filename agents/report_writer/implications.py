# MODIFIED: SUMMARY/종합시사점 프롬프트 고도화
from __future__ import annotations

import json
import logging
import re
from typing import Callable

from agents.report_writer.prompts import PROMPT_IMPLICATIONS


ResponseType = dict | str


def generate(
    lges_analysis: str,
    catl_analysis: str = "",
    comparison_matrix: str = "",
    swot: str = "",
    market_background: str = "",
    run_id: str = "unknown",
    llm_call: Callable[[str, str, str], ResponseType] | None = None,
) -> str:
    # Backward compatibility for legacy call: generate(global_findings, run_id=...)
    if not catl_analysis and not comparison_matrix and not swot and not market_background:
        market_background = lges_analysis
        lges_analysis = ""

    caller = llm_call or _default_llm_call
    user_payload = (
        f"[LGES 분석]\n{lges_analysis}\n\n"
        f"[CATL 분석]\n{catl_analysis}\n\n"
        f"[핵심 전략 비교]\n{comparison_matrix}\n\n"
        f"[SWOT 분석]\n{swot}\n\n"
        f"[시장 배경]\n{market_background}"
    )

    try:
        raw = caller(PROMPT_IMPLICATIONS, user_payload, run_id)
        data = raw if isinstance(raw, dict) else json.loads(raw)
        p1 = _strip_citations(str(data.get("paragraph_1", "")).strip())
        p2 = _strip_citations(str(data.get("paragraph_2", "")).strip())
        p3 = _strip_citations(str(data.get("paragraph_3", "")).strip())
        if not p1 or not p2 or not p3:
            raise ValueError("missing paragraph key(s)")
        return f"{p1}\n\n{p2}\n\n{p3}"
    except Exception as exc:
        logging.getLogger(f"pipeline.{run_id}").exception(
            "run_id=%s implications_generation_failed: %s", run_id, exc
        )
        return f"종합 시사점 생성 실패 (사유: {exc})"


def _default_llm_call(system_prompt: str, user_payload: str, run_id: str) -> ResponseType:
    del system_prompt, run_id
    p1 = (
        "현재 LGES와 CATL은 동일 시장을 겨냥하지만 포지셔닝의 중심축이 다르다. "
        "LGES는 지역 맞춤형 생산과 고객 포트폴리오 조정으로 변동성 방어를 우선하는 반면, CATL은 생태계 확장 속도와 표준화된 운영 효율을 통해 규모 우위를 강화한다. "
        "이 차이는 단기 실적보다 중기 시장 지배력의 형성 방식에서 더 큰 비대칭성을 만든다. "
        "따라서 전략 경쟁의 핵심은 기술 단일 우위가 아니라 실행 구조의 지속 가능성에 있다."
    )
    p2 = (
        "양사는 수요 변동, 규제 강화, 원자재 가격 변동이라는 공통 외부 리스크를 동시에 마주하고 있다. "
        "LGES는 지역·정책 노출 관리가, CATL은 규제 충돌과 통상 변수 대응이 상대적으로 중요한 취약점으로 작동한다. "
        "반면 시장 전환기에는 ESS 확장, 공급망 재편, 서비스 결합 모델이 공통 성장 기회를 제공한다. "
        "결국 리스크 통제와 기회 포착의 동시 실행 역량이 중기 성과를 좌우한다."
    )
    p3 = (
        "경영진은 시장별 수익성 기준을 재정의하고 투자 우선순위를 분기 단위로 재조정해야 한다. "
        "조달·생산·판매 데이터를 통합한 조기경보 체계를 구축해 외부 충격 대응 시간을 단축해야 한다. "
        "제품 전략은 단일 라인 최적화보다 고객군별 포트폴리오 분산을 중심으로 재설계해야 한다. "
        "또한 파트너십과 인프라 연계 전략을 통해 실행 리스크를 분산하는 운영 모델이 필요하다."
    )
    return {"paragraph_1": p1, "paragraph_2": p2, "paragraph_3": p3}


def _strip_citations(text: str) -> str:
    return re.sub(r"\[.+?,\s*\d{4}\]", "", text)
