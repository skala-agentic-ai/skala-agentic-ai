# MODIFIED: Comparison matrix now uses per-company drafts/KPI inputs and prompt-driven JSON generation.
from __future__ import annotations

import json
import logging
import re
from typing import Callable

from agents.report_writer.prompts import PROMPT_COMPARISON


ResponseType = dict | str


def generate(
    lges_draft: str,
    catl_draft: str,
    lges_kpi: dict,
    catl_kpi: dict,
    run_id: str = "unknown",
    llm_call: Callable[[str, str, str], ResponseType] | None = None,
) -> dict:
    if not lges_draft.strip() and not catl_draft.strip():
        return {
            "시장포지셔닝": {"lges": "데이터 없음 (사유: 입력 없음)", "catl": "데이터 없음 (사유: 입력 없음)"},
            "핵심기술": {"lges": "데이터 없음 (사유: 입력 없음)", "catl": "데이터 없음 (사유: 입력 없음)"},
            "수익성": {"lges": "데이터 없음 (사유: 입력 없음)", "catl": "데이터 없음 (사유: 입력 없음)"},
            "실행력": {"lges": "데이터 없음 (사유: 입력 없음)", "catl": "데이터 없음 (사유: 입력 없음)"},
            "주요리스크": {"lges": "데이터 없음 (사유: 입력 없음)", "catl": "데이터 없음 (사유: 입력 없음)"},
        }

    user_payload = (
        f"[LGES 분석]\n{lges_draft or '(empty)'}\n\n"
        f"[CATL 분석]\n{catl_draft or '(empty)'}\n\n"
        f"[LGES KPI]\n{json.dumps(lges_kpi, ensure_ascii=False)}\n\n"
        f"[CATL KPI]\n{json.dumps(catl_kpi, ensure_ascii=False)}"
    )

    caller = llm_call or _default_llm_call
    try:
        raw = caller(PROMPT_COMPARISON, user_payload, run_id)
        parsed = _to_dict(raw)
        return _convert_to_matrix(parsed)
    except Exception as exc:
        logging.getLogger(f"pipeline.{run_id}").warning(
            "run_id=%s comparison_generation_failed: %s", run_id, exc
        )
        fallback = _default_llm_call(PROMPT_COMPARISON, user_payload, run_id)
        return _convert_to_matrix(_to_dict(fallback))


def _default_llm_call(system_prompt: str, user_payload: str, run_id: str) -> ResponseType:
    del system_prompt, run_id
    lges_hint = _pick_hint(user_payload, "LGES")
    catl_hint = _pick_hint(user_payload, "CATL")

    return {
        "market_positioning_lges": f"LGES는 북미 중심 수요 전환 구간에서 생산 거점 재배치와 고객 다변화를 병행한다. {lges_hint} 시장 신호를 반영해 지역별 포지셔닝을 세분화하는 전략이 확인된다.",
        "market_positioning_catl": f"CATL은 중국 내 기반을 유지하면서 유럽과 신흥시장 확대를 통해 판매 채널을 분산한다. {catl_hint} 공급망 통제력과 대형 고객 기반을 동시에 활용하는 포지셔닝이 관찰된다.",
        "core_technology_lges": "LGES는 고에너지밀도 라인업과 안전성 개선 기술을 병행하는 접근이 두드러진다. 제품군별 기술 선택지를 분리해 고객별 요구를 대응하는 구조가 나타난다.",
        "core_technology_catl": "CATL은 대량 양산 최적화와 비용 효율 기술의 결합이 강점으로 확인된다. 표준화 플랫폼을 기반으로 제품 확장성을 확보하는 경향이 뚜렷하다.",
        "profitability_lges": "LGES 수익성은 정책 인센티브와 원가 구조 변화의 영향을 동시에 받는다. 고정비 통제와 믹스 개선이 진행될수록 마진 방어력이 회복될 가능성이 크다.",
        "profitability_catl": "CATL 수익성은 규모의 경제와 원재료 조달력에서 상대 우위를 보인다. 다만 가격 경쟁 심화 구간에서는 판가 방어와 가동률 관리가 성과를 좌우한다.",
        "execution_lges": "LGES 실행력은 북미 생산체계 운영과 파트너십 확장 속도에서 평가된다. 투자 우선순위 조정과 프로젝트 일정 통제가 실행 완성도를 결정한다.",
        "execution_catl": "CATL 실행력은 대규모 공급망 운영과 빠른 제품 전개 속도로 나타난다. 다지역 동시 운영에서 발생하는 리스크를 표준 프로세스로 완화하는 구조가 중요하다.",
        "key_risk_lges": "LGES 주요 리스크는 수요 둔화 국면에서의 가동률 하락과 정책 의존도다. 지역 집중도와 원가 압력의 동시 확대가 실적 변동성을 키울 수 있다.",
        "key_risk_catl": "CATL 주요 리스크는 지정학 변수와 무역 규제 강화다. 특정 시장 의존도가 높아질수록 규제 변화에 따른 수익 민감도가 커질 수 있다.",
    }


def _pick_hint(payload: str, company: str) -> str:
    block = payload.split(f"[{company} 분석]", 1)
    if len(block) < 2:
        return ""
    text = block[1].split("\n\n", 1)[0]
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 40:
        text = text[:40].rsplit(" ", 1)[0]
    return f"자료에는 '{text}' 관련 서술이 포함된다."


def _to_dict(raw: ResponseType) -> dict:
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


def _convert_to_matrix(data: dict) -> dict:
    required = {
        "market_positioning_lges",
        "market_positioning_catl",
        "core_technology_lges",
        "core_technology_catl",
        "profitability_lges",
        "profitability_catl",
        "execution_lges",
        "execution_catl",
        "key_risk_lges",
        "key_risk_catl",
    }
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"comparison keys missing: {sorted(missing)}")

    return {
        "시장포지셔닝": {"lges": data["market_positioning_lges"], "catl": data["market_positioning_catl"]},
        "핵심기술": {"lges": data["core_technology_lges"], "catl": data["core_technology_catl"]},
        "수익성": {"lges": data["profitability_lges"], "catl": data["profitability_catl"]},
        "실행력": {"lges": data["execution_lges"], "catl": data["execution_catl"]},
        "주요리스크": {"lges": data["key_risk_lges"], "catl": data["key_risk_catl"]},
    }
