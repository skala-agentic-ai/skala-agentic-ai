<!-- GENERATED FROM: docs/final_flowchart.md + docs/final_state_diagram.md -->
<!-- DO NOT EDIT MANUALLY — regenerate via Codex if design changes -->

# TDD 기반 구현 체크리스트

## Phase 0: 기반 설정

- [x] `constants.py` 생성  
      — `MAX_LOOP=5`, `MAX_RETRY=2`, `LLM_TIMEOUT=60`, `PIPELINE_TIMEOUT=300`, `MAX_INGEST_PAGES=100`, `CHUNK_SIZE=512`, `CHUNK_OVERLAP=64` 정의  
      — 테스트: 각 상수가 올바른 타입과 값을 가지는지 확인

- [x] State 스키마 정의 (`schemas.py`)  
      — `GlobalState`, `CompanyState`, `ReportDraft` TypedDict 정의  
      — 필드 목록은 `final_state_diagram.md`/`final_flowchart.md` 기준  
      — 테스트: 필수 필드 누락 시 즉시 실패하는지 확인  
      — 테스트: `report_draft.status` 허용값 검증 (`None/pending_validation/validated/failed`)  
      — 테스트: `global_state`(`macro_market_context`, `comparison_matrix` 포함) 필드 누락/오타를 스키마 레벨에서 차단

- [x] 상태 소유권 매핑 고정 (노드-필드 쓰기 권한 테이블)  
      — `final_state_diagram.md` 전이 라벨 + `final_flowchart.md` 상태 정의 기준으로 작성  
      — 테스트: 각 상태 필드가 지정된 소유 노드에서만 쓰이는지 검증  
      — 테스트: 타 Agent state 필드 쓰기 시도 시 실패 처리 검증

- [x] 사양 우선순위 규칙 고정  
      — 상태 전이는 `final_state_diagram.md`, 목차/담당 범위는 `final_flowchart.md`를 기준으로 적용  
      — 테스트: LGES 담당 범위 `2.1~2.4`, CATL 담당 범위 `3.1~3.4`가 강제되는지 검증

- [x] SourceDoc 스키마 정의  
      — `source_type` / `source_url` / `published_at` / `retrieved_at` 필수 필드  
      — 테스트: 필드 누락 시 `ValidationError` 발생 확인

## Phase 1: 데이터 계층

- [x] `retrieval/pdf_loader.py` 구현  
      — `load_pdfs_from_dir(data_dir, domain) -> list[SourceDoc]`  
      — 테스트: `data/LGES/` PDF 파싱 -> `SourceDoc` 반환  
      — 테스트: `data/CATL/` PDF 파싱 -> `SourceDoc` 반환  
      — 테스트: `data/market/` PDF 파싱 -> `SourceDoc` 반환  
      — 테스트: `MAX_INGEST_PAGES` 초과 시 경고 후 스킵  
      — 테스트: 손상된 PDF 스킵 (크래시 없음)  
      — 테스트: 도메인 간 교차 ingest 방지 (`domain` 파라미터 검증)

- [x] `retrieval/vector_store.py` 구현  
      — `ingest(domain, docs)` / `query(domain, queries) -> list[SourceDoc]`  
      — 테스트: ingest 후 query 결과 반환 확인  
      — 테스트: 타 도메인 query 결과가 반환되지 않음 확인  
      — 테스트: 빈 docs ingest 시 `RuntimeError` 발생

- [x] `retrieval/web_search.py` 구현  
      — `search(queries) -> list[SourceDoc]`  
      — 테스트: 결과가 SourceDoc 스키마를 준수하는지 확인  
      — 테스트: API 실패 시 빈 리스트 반환 + 로그 기록

## Phase 2: Preprocessing 노드

- [x] `agents/preprocessing/query_expansion.py`  
      — `expand(user_query) -> list[str]`  
      — 테스트: 단일 쿼리 -> 복수 확장 쿼리 반환  
      — 테스트: 빈 쿼리 입력 시 `ValueError` 발생  
      — 테스트: `global_state.user_query` 업데이트 확인

- [x] `agents/preprocessing/bias_mitigation.py`  
      — `mitigate(expanded_queries) -> list[str]`  
      — 테스트: 긍정/부정 양방향 쿼리가 모두 포함되는지 확인  
      — 테스트: `global_state.bias_queries` 업데이트 확인

- [x] `agents/preprocessing/router.py`  
      — `route(bias_queries) -> dict` (`task_routes`)  
      — 테스트: CATL/LGES/Market 세 키가 모두 존재하는지 확인  
      — 테스트: `global_state.task_routes` 업데이트 확인

## Phase 3: Agent 공통 노드

- [x] `agents/common/quality_check.py`  
      — `check(evidence_pool) -> passed: bool, reason: str`  
      — 테스트: 출처 없는 증거 -> `passed=False`  
      — 테스트: 최신성 기준 미달 -> `passed=False`  
      — 테스트: 정상 증거 -> `passed=True`

- [x] `agents/common/content_writer.py`  
      — `write(evidence_pool, section_scope) -> draft: str`  
      — 테스트: 빈 `evidence_pool` -> `"데이터 없음 (사유: ...)"` 반환  
      — 테스트: 모든 사실 주장에 `[출처명, YYYY]` 인용 포함 확인

- [x] `agents/common/content_evaluator.py`  
      — `evaluate(draft, section_scope) -> approved: bool, retry_instruction: str`  
      — 테스트: 인용 없는 draft -> `approved=False`  
      — 테스트: 반대 근거 없는 draft -> `approved=False`  
      — 테스트: 정상 draft -> `approved=True`  
      — 테스트: `approved=True` 시 `company_state.approved=true` 설정 확인

## Phase 4: Agent 루프

- [x] `agents/market/agent.py`  
      — `run(task_routes, global_state) -> market_state`  
      — 테스트: `WebSearch -> PaperSearch -> QualityCheck -> WriteContent -> ContentEval` 순서 실행  
      — 테스트: `ContentEval` 미흡 시 `WebSearch`부터 재실행  
      — 테스트: `MaxLoop=5` 초과 시 강제 종료 + `retry_instruction` 기록  
      — 테스트: `market_state`가 `lges_state`/`catl_state`를 참조하지 않음

- [x] `agents/lges/agent.py`  
      — `run(task_routes, global_state) -> lges_state`  
      — 테스트: 위 `market/agent.py`와 동일 구조 검증  
      — 테스트: 담당 목차가 `2.1~2.4`인지 확인  
      — 테스트: `lges_state`가 `catl_state`/`market_state`를 참조하지 않음

- [x] `agents/catl/agent.py`  
      — `run(task_routes, global_state) -> catl_state`  
      — 테스트: 위 `market/agent.py`와 동일 구조 검증  
      — 테스트: 담당 목차가 `3.1~3.4`인지 확인  
      — 테스트: `catl_state`가 `lges_state`/`market_state`를 참조하지 않음

- [x] 병렬 실행 래퍼  
      — `execute_parallel(market, lges, catl) -> (market_state, lges_state, catl_state)`  
      — 테스트: 세 Agent가 병렬로 실행되는지 확인  
      — 테스트: 한 Agent 실패가 다른 Agent를 중단시키지 않음

## Phase 5: Supervisor Review

- [x] `agents/supervisor/global_consistency.py`  
      — `check(market_state, lges_state, catl_state) -> consistency_report: str`  
      — 테스트: 숫자 불일치 탐지 확인  
      — 테스트: 연도 불일치 탐지 확인  
      — 테스트: 반대 근거 누락 탐지 확인  
      — 테스트: `global_state.consistency_report` 업데이트 확인

- [x] `agents/supervisor/quality_gate.py`  
      — `judge(consistency_report) -> passed: bool, retry_instruction: str`  
      — 테스트: Gate1~Gate5 각각에 대해 실패 케이스 검증  
      — 테스트: 전체 통과 시 `passed=True`  
      — 테스트: 기준 미달 시 `retry_instruction` 내용이 비어있지 않음

- [x] `agents/supervisor/final_synth.py`  
      — `synthesize(market_state, lges_state, catl_state) -> global_findings: str`  
      — 테스트: 세 state의 draft가 모두 반영되는지 확인  
      — 테스트: `global_state.global_findings` 업데이트 확인  
      — 테스트: `global_state.macro_market_context`가 시장 배경 근거로 갱신되는지 확인  
      — 테스트: `company_state` 필드를 직접 수정하지 않음

- [x] Supervisor Review 재루프 제어  
      — 테스트: 기준 미달 -> `Router` 재실행  
      — 테스트: `MaxLoop=5` 초과 -> Force Exit  
      — 테스트: 재루프 시 `global_state.task_routes` 재설정 확인

## Phase 6: 보고서 생성 Agent

- [x] `agents/report_writer/comparison_matrix.py`  
      — `generate(global_findings) -> comparison_matrix: dict`  
      — 테스트: 5개 항목(시장포지셔닝/핵심기술/수익성/실행력/주요리스크) 모두 존재  
      — 테스트: LGES/CATL 키가 분리되어 있음 (`_lges` / `_catl`)  
      — 테스트: 빈 `global_findings` -> `"데이터 없음 (사유: ...)"` 반환

- [x] `agents/report_writer/swot.py`  
      — `generate(global_findings) -> swot: dict`  
      — 테스트: `lges`/`catl` 각각 S/W/O/T 4개 키 모두 존재  
      — 테스트: 각 항목이 evidence 기반인지 확인 (인용 포함)

- [x] `agents/report_writer/implications.py`  
      — `generate(global_findings) -> implications: str`  
      — 테스트: 결론이 근거 없는 단정을 포함하지 않음  
      — 테스트: 인용 `[출처명, YYYY]` 포함 확인

- [x] `agents/report_writer/summary.py`  
      — `generate(comparison_matrix, swot, implications) -> summary: str`  
      — 테스트: 핵심 결론 3~5개 bullet 포함  
      — 테스트: `comparison_matrix`/`swot`/`implications`가 모두 완성된 후에만 실행  
      — 테스트: 0.5페이지(약 400자) 이내인지 확인

- [x] `agents/report_writer/reference_compiler.py`  
      — `compile(all_sections) -> reference: list[dict]`  
      — 테스트: 본문에서 실제 인용된 출처만 포함  
      — 테스트: 미사용 출처가 포함되지 않음  
      — 테스트: SUMMARY와 병렬 실행 가능한지 확인 (독립성)

- [x] `agents/report_writer/agent.py` (통합)  
      — `run(global_findings) -> report_draft`  
      — 테스트: fork1 병렬 실행 (`comparison_matrix` / `swot` / `implications`)  
      — 테스트: join1 후 fork2 병렬 실행 (`summary` / `reference`)  
      — 테스트: `market_background` / `lges_analysis` / `catl_analysis` 섹션이 채워지는지 확인  
      — 테스트: 초기 상태 `None`에서 DraftComplete 시 `report_draft.status=pending_validation` 전이 확인  
      — 테스트: join2 후 DraftComplete -> `report_draft.status = pending_validation`  
      — 테스트: `global_findings`만 입력으로 받음 (`company_state` 참조 없음)  
      — 테스트: 저장 호출이 존재하지 않음 (파일 저장 책임 없음)  
      — 테스트: LLM 실패 시 해당 섹션 `"섹션 생성 실패 (사유: ...)"` 마킹 후 계속 진행  
      — 테스트: `MaxAllowedFailures=2` 초과 시 `ReportWriterError` 발생

## Phase 7: Supervisor 최종 처리

- [x] `agents/supervisor/final_validation.py`  
      — `validate(report_draft) -> passed: bool, failed_gates: list`  
      — 테스트: Gate1~Gate5 각각 실패 케이스 검증  
      — 테스트: `report_draft.status = validated` 설정 확인  
      — 테스트: 실패 시 `report_draft.status = failed` + 초기화 확인

- [x] `agents/supervisor/formatter.py`  
      — `format(report_draft) -> markdown: str`  
      — 테스트: 목차 순서 고정 확인 (`SUMMARY / 1~6 / REFERENCE`)  
      — 테스트: 모든 표가 올바른 Markdown 형식인지 확인  
      — 테스트: `report_draft`가 `None`이면 `FormattingError` 발생

- [x] `agents/supervisor/report_saver.py`  
      — `save(markdown, run_id) -> report_path: str`  
      — 테스트: 파일명 형식 `report_{run_id}_{timestamp}.md` 확인  
      — 테스트: `outputs/` 디렉터리에 저장되는지 확인  
      — 테스트: UTF-8 인코딩으로 저장되는지 확인  
      — 테스트: `global_state.report_path` 업데이트 확인  
      — 테스트: 보고서 저장 함수가 Supervisor 경로에서만 호출되는지 확인

- [x] 최종 검증 실패 재시도  
      — 테스트: 검증 실패 -> 보고서 생성 Agent 재실행  
      — 테스트: `MaxRetry=2` 초과 -> 현재 draft + 한계 명시 후 저장

## Phase 8: 통합 테스트

- [x] Preprocessing -> AgentExecution 통합  
      — 테스트: Router 출력이 세 Agent에 올바르게 전달되는지 확인

- [x] AgentExecution -> SupervisorReview 통합  
      — 테스트: 세 Agent `approved=True` 후 SupervisorReview 진입 확인  
      — 테스트: 한 Agent `approved=False` 상태에서 SupervisorReview 진입 불가 확인

- [x] SupervisorReview -> ReportWriter 통합  
      — 테스트: QualityGate pass -> `global_findings` 전달 -> ReportWriter 실행  
      — 테스트: QualityGate fail -> Router 재루프 실행

- [x] ReportWriter -> FinalOutput 통합  
      — 테스트: `report_draft.status=pending_validation` -> FinalValidation 진입  
      — 테스트: FinalValidation pass -> Formatting -> SaveReport 순서 실행  
      — 테스트: FinalValidation fail -> ReportWriter 재실행  
      — 테스트: `report_draft.status` 전이(`None -> pending_validation -> validated/failed`)가 허용 경로에서만 발생

- [x] 전체 파이프라인 E2E  
      — 테스트: 대표 쿼리 1 -> 보고서 목차 구조 유지 확인  
      — 테스트: 대표 쿼리 2 -> 보고서 목차 구조 유지 확인  
      — 테스트: `PIPELINE_TIMEOUT=300s` 초과 시 Force Exit 동작 확인  
      — 테스트: `run_id`가 모든 로그 항목에 포함되어 있는지 확인

## Phase 9: 회귀 테스트

- [x] 보고서 목차 완결성  
      — `SUMMARY` / 섹션1~6 / `REFERENCE` 모두 존재  
      — 각 섹션이 비어있지 않음

- [x] 인용 완결성  
      — 보고서 본문의 모든 사실 주장에 `[출처명, YYYY]` 존재  
      — `REFERENCE`의 모든 항목이 본문에서 인용됨

- [x] 상태 오염 없음  
      — 실행 후 `catl_state` / `lges_state` / `market_state`가 서로 다른 값을 가짐  
      — `global_state`가 `company_state` 필드를 직접 포함하지 않음
