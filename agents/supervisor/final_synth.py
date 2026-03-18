from __future__ import annotations

from schemas import CompanyState, GlobalState


def synthesize(
    market_state: CompanyState,
    lges_state: CompanyState,
    catl_state: CompanyState,
    global_state: GlobalState | None = None,
) -> str:
    findings = "\n".join(
        [
            "<<<MARKET>>>",
            market_state["draft"],
            "<<<END_MARKET>>>",
            "<<<LGES>>>",
            lges_state["draft"],
            "<<<END_LGES>>>",
            "<<<CATL>>>",
            catl_state["draft"],
            "<<<END_CATL>>>",
        ]
    )
    if global_state is not None:
        global_state["global_findings"] = findings
        global_state["macro_market_context"] = market_state["draft"]
    return findings
