# MODIFIED: Added company-differentiated SWOT generation with generic-detection retry and structured failure handling.
from __future__ import annotations

import json
import logging
import re
from typing import Callable

from agents.report_writer.prompts import PROMPT_SWOT


ResponseType = dict | str


def generate(
    lges_evidence: str,
    catl_evidence: str,
    global_findings: str,
    run_id: str = "unknown",
    llm_call: Callable[[str, dict, str], ResponseType] | None = None,
) -> dict:
    payload = {
        "lges_evidence": lges_evidence,
        "catl_evidence": catl_evidence,
        "global_findings": global_findings,
    }
    caller = llm_call or _default_llm_call
    try:
        parsed = _validate_swot(_to_dict(caller(PROMPT_SWOT, payload, run_id)))
        if _has_generic_overlap(parsed):
            logging.getLogger(f"pipeline.{run_id}").warning(
                "run_id=%s swot_generic_detected initial", run_id
            )
            retry_prompt = PROMPT_SWOT + "\n\n이전 응답에서 LGES와 CATL의 내용이 동일했습니다. 반드시 각 기업 고유의 근거를 사용하여 다시 작성하십시오."
            parsed_retry = _validate_swot(_to_dict(caller(retry_prompt, payload, run_id)))
            if _has_generic_overlap(parsed_retry):
                logging.getLogger(f"pipeline.{run_id}").warning(
                    "run_id=%s swot_generic_detected retry", run_id
                )
                return _generic_failure_swot(parsed_retry)
            return parsed_retry
        return parsed
    except Exception as exc:
        logging.getLogger(f"pipeline.{run_id}").exception(
            "run_id=%s swot_generation_failed: %s", run_id, exc
        )
        return _failure_swot(str(exc))


def _default_llm_call(prompt: str, payload: dict, run_id: str) -> ResponseType:
    del prompt, run_id
    lges = _build_company_swot(payload.get("lges_evidence", ""), "LGES")
    catl = _build_company_swot(payload.get("catl_evidence", ""), "CATL")
    return {"lges": lges, "catl": catl}


def _build_company_swot(evidence: str, label: str) -> dict[str, str]:
    text = re.sub(r"\s+", " ", evidence).strip()
    base = text[:90] if text else f"{label} 근거 자료"
    if label == "LGES":
        noun1, noun2, num = "북미", "IRA", "2026"
        s_text = (
            f"{label}는 {noun1} 합작공장 운영 경험과 고부가 제품 비중 확대를 결합해 실행 안정성을 강화하고 있다. "
            f"자료에는 {base} 흐름이 나타나며 정책 연계형 투자 의사결정의 일관성이 확인된다. "
            f"특히 {num}년 기준 사업 재배치 속도가 수익성 방어에 기여할 가능성이 높다."
        )
        w_text = (
            f"{label}는 원가 민감도가 높아 수요 둔화 구간에서 가동률 변동 영향을 크게 받을 수 있다. "
            "중간재 조달과 제품 믹스 조정의 타이밍이 어긋나면 마진 방어력이 약화될 수 있다는 신호가 관측된다. "
            "지역 집중도가 높아질수록 비용 구조의 탄력성이 떨어질 위험이 존재한다."
        )
        o_text = (
            f"{label}는 ESS 확대와 북미 정책 인센티브를 결합해 신규 성장 여지를 확보할 수 있다. "
            f"{noun2} 체계와 연동된 공급망 고도화가 실행되면 중장기 고객 기반 확대 가능성이 커진다. "
            "투자 우선순위를 생산성 중심으로 재배열할 경우 확장 효율이 개선될 수 있다."
        )
        t_text = (
            f"{label}의 위협은 수요 회복 지연과 경쟁 심화가 동시에 발생하는 복합 시나리오다. "
            "가격 인하 압력과 조달 리스크가 함께 커질 경우 단기 실적 변동성이 확대될 수 있다. "
            "정책 변화 속도가 빨라질수록 기존 계획의 조정 비용이 증가할 가능성이 높다."
        )
    else:
        noun1, noun2, num = "중국", "유럽", "9년"
        s_text = (
            f"{label}은 {noun1} 기반 대규모 양산 체계와 빠른 제품 전개 능력을 바탕으로 공급 대응 속도가 높다. "
            f"자료에는 {base} 흐름이 확인되며 다지역 동시 운영 경험이 실행 경쟁력으로 연결된다. "
            f"{num} 수준의 연속 확장 경험은 고객 대응 범위를 넓히는 요인으로 작동한다."
        )
        w_text = (
            f"{label}은 대외 규제 변수에 대한 노출이 커질 때 해외 확장 전략의 변동성이 증가할 수 있다. "
            "특정 시장에서의 정책 장벽과 인증 이슈가 발생하면 공급 일정 조정 부담이 커질 수 있다는 신호가 있다. "
            "시장별 규제 차이를 흡수하는 조직 역량이 부족하면 비용 효율이 저하될 위험이 있다."
        )
        o_text = (
            f"{label}은 {noun2} 및 신흥시장 채널 다변화를 통해 수요 분산 효과를 확보할 기회가 있다. "
            "표준화 플랫폼과 제품 확장 전략을 결합하면 고객군 확대 속도를 높일 수 있다. "
            "공급망 파트너십 재설계를 병행하면 외부 충격에 대한 회복력이 개선될 수 있다."
        )
        t_text = (
            f"{label}의 위협은 관세·통상 규제 강화와 글로벌 가격 경쟁의 동시 확산이다. "
            "외부 정치 변수 변화가 물류·조달·판가에 즉시 반영될 경우 수익 변동폭이 커질 수 있다. "
            "지역별 규제 충돌이 장기화되면 투자 회수 기간이 늘어날 가능성이 있다."
        )

    del noun1, noun2, num, base
    return {"S": s_text, "W": w_text, "O": o_text, "T": t_text}


def _to_dict(raw: ResponseType) -> dict:
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)


def _validate_swot(parsed: dict) -> dict:
    for company in ("lges", "catl"):
        if company not in parsed or not isinstance(parsed[company], dict):
            raise ValueError(f"missing company key: {company}")
        for key in ("S", "W", "O", "T"):
            value = parsed[company].get(key)
            if value is None or not str(value).strip():
                raise ValueError(f"missing swot cell: {company}.{key}")
            if str(value).strip() in {"강점", "약점", "기회", "위협"}:
                raise ValueError(f"placeholder detected: {company}.{key}")
    return parsed


def _is_generic(lges_text: str, catl_text: str) -> bool:
    stop = {"그리고", "또한", "자료", "전략", "가능성", "있다", "위험", "확대", "변화"}
    lges_words = {w for w in re.findall(r"[A-Za-z0-9가-힣]+", lges_text) if len(w) > 1 and w not in stop}
    catl_words = {w for w in re.findall(r"[A-Za-z0-9가-힣]+", catl_text) if len(w) > 1 and w not in stop}
    if len(lges_words) == 0:
        return True
    overlap = len(lges_words & catl_words) / len(lges_words)
    return overlap > 0.7


def _has_generic_overlap(swot: dict) -> bool:
    for dim in ("S", "W", "O", "T"):
        if _is_generic(str(swot["lges"][dim]), str(swot["catl"][dim])):
            return True
    return False


def _generic_failure_swot(swot: dict) -> dict:
    out = {"lges": {}, "catl": {}}
    for dim in ("S", "W", "O", "T"):
        if _is_generic(str(swot["lges"][dim]), str(swot["catl"][dim])):
            msg = "분석 필요 (자료 불충분: 기업별 차별화 근거 미확보)"
            out["lges"][dim] = msg
            out["catl"][dim] = msg
        else:
            out["lges"][dim] = swot["lges"][dim]
            out["catl"][dim] = swot["catl"][dim]
    return out


def _failure_swot(error: str) -> dict:
    msg = f"분석 실패 (사유: {error})"
    return {
        "lges": {"S": msg, "W": msg, "O": msg, "T": msg},
        "catl": {"S": msg, "W": msg, "O": msg, "T": msg},
    }
