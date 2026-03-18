from __future__ import annotations

from schemas import GlobalState


def mitigate(expanded_queries: list[str], global_state: GlobalState | None = None) -> list[str]:
    bias_queries: list[str] = []
    for q in expanded_queries:
        bias_queries.append(f"{q} 긍정")
        bias_queries.append(f"{q} 부정")
    if global_state is not None:
        global_state["bias_queries"] = bias_queries
    return bias_queries
