from __future__ import annotations

from schemas import ReportDraft


def validate(report_draft: ReportDraft) -> tuple[bool, list[str]]:
    failed: list[str] = []
    if report_draft.get("status") != "pending_validation":
        failed.append("Gate1: invalid status")
    if not report_draft.get("summary"):
        failed.append("Gate2: summary missing")
    if not report_draft.get("reference"):
        failed.append("Gate3: reference missing")
    if not report_draft.get("comparison_matrix"):
        failed.append("Gate4: comparison missing")
    for sec in ("market_background", "lges_analysis", "catl_analysis", "implications"):
        if not report_draft.get(sec):
            failed.append(f"Gate5: {sec} missing")
            break

    if failed:
        report_draft["status"] = "failed"
        return False, failed
    report_draft["status"] = "validated"
    return True, []
