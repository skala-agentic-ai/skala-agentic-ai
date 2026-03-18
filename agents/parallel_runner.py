from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from schemas import CompanyState


def execute_parallel(
    market: Callable[[], CompanyState],
    lges: Callable[[], CompanyState],
    catl: Callable[[], CompanyState],
) -> tuple[CompanyState, CompanyState, CompanyState]:
    with ThreadPoolExecutor(max_workers=3) as ex:
        fm = ex.submit(market)
        fl = ex.submit(lges)
        fc = ex.submit(catl)

        def safe(future) -> CompanyState:
            try:
                return future.result()
            except Exception as exc:  # explicit, no silent pass
                return {
                    "evidence_pool": [],
                    "draft": "",
                    "pro_arguments": [],
                    "con_arguments": [],
                    "kpi_snapshot": {},
                    "swot_draft": {},
                    "quality_score": 0.0,
                    "approved": False,
                    "retry_instruction": f"agent failed: {exc}",
                }

        return safe(fm), safe(fl), safe(fc)
