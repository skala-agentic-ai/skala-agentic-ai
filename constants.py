"""System-wide constants for pipeline control and defaults."""

MAX_LOOP = 5
MAX_RETRY = 2
LLM_TIMEOUT = 60
PIPELINE_TIMEOUT = 300
MAX_INGEST_PAGES = 100
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
MAX_ALLOWED_FAILURES = 2

ALLOWED_REPORT_STATUS = {None, "pending_validation", "validated", "failed"}

QUALITY_GATES = ("gate1", "gate2", "gate3", "gate4", "gate5")

REPORT_TOC_ORDER = (
    "SUMMARY",
    "1. 시장 배경",
    "2. LG에너지솔루션 전략 분석",
    "3. CATL 전략 분석",
    "4. 핵심 전략 비교",
    "5. SWOT 분석",
    "6. 종합 시사점",
    "REFERENCE",
)
