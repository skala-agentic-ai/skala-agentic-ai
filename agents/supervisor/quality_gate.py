from __future__ import annotations

from constants import QUALITY_GATES


def judge(consistency_report: str) -> tuple[bool, str]:
    if consistency_report == "통과":
        return True, ""
    details = f"gate fail ({', '.join(QUALITY_GATES)}): {consistency_report}"
    return False, details
