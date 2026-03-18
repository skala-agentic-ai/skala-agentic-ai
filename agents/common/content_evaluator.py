# MODIFIED: Evaluates section quality using prose + evidence_references instead of inline citation markers.
from __future__ import annotations

from schemas import CompanyState


def evaluate(draft: str, section_scope: str, company_state: CompanyState | None = None) -> tuple[bool, str]:
    del section_scope
    if not draft.strip():
        instruction = "본문 누락"
        if company_state is not None:
            company_state["retry_instruction"] = instruction
        return False, instruction
    if company_state is None or not company_state.get("evidence_references"):
        instruction = "근거 참조 누락"
        if company_state is not None:
            company_state["retry_instruction"] = instruction
        return False, instruction
    if "리스크" not in draft and "위협" not in draft and "불확실" not in draft:
        instruction = "반대 근거 누락"
        if company_state is not None:
            company_state["retry_instruction"] = instruction
            return False, instruction
    if company_state is not None:
        company_state["approved"] = True
        company_state["retry_instruction"] = ""
    return True, ""
