from __future__ import annotations

from schemas import GlobalState


def route(bias_queries: list[str], global_state: GlobalState | None = None) -> dict[str, str]:
    joined = " | ".join(bias_queries)
    routes = {
        "catl": f"CATL focus: {joined}",
        "lges": f"LGES focus: {joined}",
        "market": f"MARKET focus: {joined}",
    }
    if global_state is not None:
        global_state["task_routes"] = routes
    return routes
