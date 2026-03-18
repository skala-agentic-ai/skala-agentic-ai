from __future__ import annotations

import argparse
from pathlib import Path

from pipeline import run_pipeline

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency fallback
    load_dotenv = None


DEFAULT_QUERY = "LG에너지솔루션과 CATL의 2026년 전략을 비교 분석하고 투자 관점 시사점을 작성해줘"
DEFAULT_RUN_ID = "app_final"
REPORT_DIR = Path("report")
FINAL_REPORT_NAME = "final_report.md"


def _prepare_report_dir(report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    for existing in report_dir.glob("*.md"):
        existing.unlink()


def main() -> int:
    if load_dotenv is not None:
        load_dotenv()

    parser = argparse.ArgumentParser(description="Generate the final report into report/final_report.md")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="User query for the pipeline")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID, help="Run ID for traceability")
    args = parser.parse_args()

    state = run_pipeline(args.query, run_id=args.run_id)
    report_path = str(state.get("report_path", "")).strip()
    if not report_path:
        raise RuntimeError("Report path is empty. Pipeline likely exited before final save.")
    generated_path = Path(report_path)
    if not generated_path.exists() or generated_path.is_dir():
        raise RuntimeError(f"Report was not generated: {generated_path}")

    _prepare_report_dir(REPORT_DIR)
    final_report_path = REPORT_DIR / FINAL_REPORT_NAME
    generated_path.replace(final_report_path)
    print(final_report_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
