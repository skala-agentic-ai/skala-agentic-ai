from __future__ import annotations

from schemas import GlobalState


def expand(user_query: str, global_state: GlobalState | None = None) -> list[str]:
    q = user_query.strip()
    if not q:
        raise ValueError("empty query")
    expanded = [q, f"{q} 최신 동향", f"{q} 리스크", f"{q} 반대 근거"]
    if global_state is not None:
        global_state["user_query"] = q
    return expanded
