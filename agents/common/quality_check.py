from __future__ import annotations

from datetime import datetime

from schemas import SourceDoc


def check(evidence_pool: list[SourceDoc]) -> tuple[bool, str]:
    if not evidence_pool:
        return False, "no evidence"
    for doc in evidence_pool:
        if not doc.get("source_name"):
            return False, "missing citation"
        year = doc.get("year", "0000")
        if year.isdigit() and int(year) < 2020:
            return False, "stale evidence"
    return True, "ok"
