from __future__ import annotations

from datetime import datetime
from pathlib import Path

from schemas import GlobalState


def save(markdown: str, run_id: str, global_state: GlobalState | None = None) -> str:
    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"report_{run_id}_{timestamp}.md"
    path.write_text(markdown, encoding="utf-8")
    resolved = str(path.resolve())
    if global_state is not None:
        global_state["report_path"] = resolved
    return resolved
