from __future__ import annotations

import re

from schemas import CompanyState, GlobalState


def check(market_state: CompanyState, lges_state: CompanyState, catl_state: CompanyState, global_state: GlobalState | None = None) -> str:
    drafts = [market_state["draft"], lges_state["draft"], catl_state["draft"]]
    years = set(re.findall(r"(20\\d{2})", "\n".join(drafts)))
    issues: list[str] = []
    if len(years) > 1:
        issues.append("연도 불일치")
    if any("반대" not in d and "리스크" not in d for d in drafts):
        issues.append("반대 근거 누락")
    nums = re.findall(r"\\d+[\\.,]?\\d*", "\n".join(drafts))
    if len(nums) >= 2 and len(set(nums[:2])) > 1:
        issues.append("숫자 불일치 가능성")
    report = "통과" if not issues else "; ".join(issues)
    if global_state is not None:
        global_state["consistency_report"] = report
    return report
