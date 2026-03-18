<!-- GENERATED FROM: docs/final_flowchart.md + docs/final_state_diagram.md -->
<!-- DO NOT EDIT MANUALLY — regenerate via Codex if design changes -->

# 코드 품질 원칙서 (전면 개정)

## 1. 목적
본 원칙서는 배터리 시장 전략 분석 멀티에이전트 시스템의 설계/구현/검증 기준을 정의한다. 적용 범위는 사용자 쿼리 입력부터 최종 보고서 저장까지의 전체 파이프라인이며, 목표는 다음 네 가지다.

- 재현 가능성: 동일 입력과 동일 상태 규칙에서 동일한 제어 흐름을 보장한다.
- 신뢰성: 품질 게이트, 루프 상한, 타임아웃을 통해 실패를 통제한다.
- 유지보수성: 상태 소유권, 상수화, 책임 분리로 변경 영향을 국소화한다.
- 분석 일관성: Agent 간 비교 가능성과 출처 기반 결론을 유지한다.

## 2. 아키텍처 원칙
- Supervisor Agent는 Preprocessing(`QueryExpansion -> BiasMitigation -> Router`)부터 최종 보고서 저장까지 전체 흐름을 제어한다.
- CATL/LGES/Market 세 Agent는 병렬 실행하며 `catl_state`, `lges_state`, `market_state`는 물리적으로 분리한다.
- Agent 간 state 직접 참조/수정은 금지한다.
- 보고서 생성 Agent는 Supervisor Review 통과 후 독립 노드로 실행한다.
- 보고서 생성 Agent 입력은 `global_findings`만 허용하며 `company_state` 직접 참조를 금지한다.
- 최종 검증과 `.md` 저장은 Supervisor Agent가 직접 수행한다.
- 보고서 생성 Agent는 저장 책임을 갖지 않는다.

## 3. 상태(State) 원칙
### 3.1 상태 필드와 소유 주체

#### global_state
- `user_query`: `QueryExpansion`에서 갱신
- `bias_queries`: `BiasMitigation`에서 갱신
- `task_routes`: `Router`, `RetryInstruction` 재루프 시 갱신
- `macro_market_context`: Supervisor 통합 컨텍스트 단계에서 관리
- `global_findings`: `FinalSynth` 또는 `QualityGate` 통과 경로에서 갱신
- `comparison_matrix`: 보고서 생성 결과를 Supervisor 컨텍스트에서 참조
- `consistency_report`: `GlobalConsistency`에서 갱신
- `retry_instruction`: Agent `ContentEval`/Supervisor `RetryInstruction`에서 생성
- `final_report`: `Formatting`에서 갱신
- `report_path`: `SaveReport`에서 갱신

#### company_state (market/lges/catl 공통)
- `evidence_pool`: 각 Agent `QualityCheck` 통과 시 갱신
- `draft`: 각 Agent `WriteContent`에서 갱신
- `pro_arguments`, `con_arguments`, `kpi_snapshot`, `swot_draft`, `quality_score`: 해당 Agent 내부 품질/작성 단계에서 갱신
- `approved`: 해당 Agent `ContentEval`만 `true` 설정 가능
- `retry_instruction`: 해당 Agent `ContentEval` 미흡 시 갱신

#### report_draft
- `comparison_matrix`: `ComparisonMatrix`에서 갱신
- `swot`: `SWOTGrid`에서 갱신
- `implications`: `Implications`에서 갱신
- `summary`: `Summary`에서 갱신
- `reference`: `ReferenceCompile`에서 갱신
- `market_background`, `lges_analysis`, `catl_analysis`: 통합 초안 조립 단계에서 갱신
- `status`: `DraftComplete`, `FinalValidation`에서만 전이

### 3.2 상태 쓰기 권한
- 상태는 소유 주체 노드만 쓴다.
- 타 Agent state 필드 직접 수정 금지.
- 읽기와 쓰기 책임을 분리하고, 쓰기는 지정 노드에서만 허용한다.

### 3.3 `report_draft.status` 전이 규칙
- `None -> pending_validation`: `DraftComplete`
- `pending_validation -> validated`: `FinalValidation` 통과 경로
- `pending_validation -> failed`: `FinalValidation` 실패 경로
- `failed -> pending_validation`: 보고서 생성 Agent 재실행 후 `DraftComplete`

### 3.4 `approved` 플래그 규칙
- `market_state.approved`, `lges_state.approved`, `catl_state.approved`는 각 Agent의 `ContentEval` 노드만 `true`로 설정할 수 있다.

## 4. 루프 및 제어 원칙
- Agent 내부 루프: `ContentEval` 미흡 시 `WebSearch`부터 재실행한다.
- Agent 내부 루프 상한: `MaxLoop = 5`. 초과 시 `retry_instruction`에 실패 사유 기록 후 강제 종료한다.
- Supervisor Review 재루프: 기준 미달 시 `Router`부터 재실행한다.
- Supervisor 재루프 상한: `MaxLoop = 5`. 초과 시 Force Exit 처리한다.
- 최종 검증 실패 재시도: 보고서 생성 Agent를 재실행한다.
- 최종 검증 재시도 상한: `MaxRetry = 2`. 초과 시 현재 draft와 한계를 명시해 저장한다.
- 모든 상한값은 상수로 정의한다. 코드 내 매직 넘버 사용을 금지한다.
- Timeout 정책:
  - 개별 LLM 호출: `60s`
  - 전체 파이프라인: `300s`

## 5. 데이터 / RAG 원칙
- `data/market/`, `data/LGES/`, `data/CATL/`의 PDF는 각 도메인 Agent Vector DB에만 ingest한다.
- 도메인 간 교차 ingest를 금지한다.
- 각 `SourceDoc`은 다음 4개 필드를 필수 포함한다.
  - `source_type`
  - `source_url`
  - `published_at`
  - `retrieved_at`
- 최대 ingest 페이지는 도메인별 독립적으로 `100페이지`를 적용한다.
- RAG 조회 결과 기반 문장은 출처 없는 생성(무인용 사실 주장)을 금지한다.
- Web Search 결과도 동일한 `SourceDoc` 스키마로 저장한다.

## 6. 보고서 생성 원칙
- `핵심 전략 비교표`, `SWOT 그리드`, `종합 시사점`은 병렬 생성한다.
- `SUMMARY`는 위 3개 결과가 모두 완성된 후 생성한다.
- `REFERENCE`는 `SUMMARY`와 병렬 컴파일하되, 본문에서 실제 인용된 출처만 포함한다.
- 미사용 출처 포함을 금지한다.
- 보고서 목차 순서는 고정한다.
  - `SUMMARY`
  - `1. 시장배경`
  - `2. LGES분석`
  - `3. CATL분석`
  - `4. 핵심전략비교`
  - `5. SWOT`
  - `6. 종합시사점`
  - `REFERENCE`
- 모든 사실 주장에 인라인 인용 `[출처명, YYYY]`을 필수로 포함한다.

## 7. 코드 작성 규칙
- 모든 Agent I/O는 `TypedDict` 또는 `Pydantic`으로 스키마를 고정한다.
- 함수는 단일 책임 원칙을 따른다.
- `except: pass`를 금지한다.
- 모든 예외는 `run_id`와 함께 로깅한다.
- 모든 로그 항목에 `run_id`를 포함한다.
- 상수는 별도 `constants.py`에 정의한다.
- API 키/비밀값 하드코딩을 금지한다.
- I/O 처리, 비즈니스 로직, 포맷팅 로직을 분리한다.

## 8. 테스트 원칙
- 단위 테스트: 각 노드의 상태 전이, 루프 조건 판정, 품질 게이트 판정을 검증한다.
- 통합 테스트: `Supervisor -> Agent -> Evaluation -> Supervisor Review -> 보고서 생성 -> 최종 처리`를 검증한다.
- 회귀 테스트: 대표 쿼리 2종으로 보고서 목차 구조/필수 섹션 유지 여부를 검증한다.
- 신규 기능은 테스트를 먼저 작성한 뒤 구현한다.
- 실패 테스트 방치를 금지한다.

## 9. 금지 사항
- 근거 없는 결론 생성
- Agent 간 state 직접 참조
- 예외 무시(`except: pass`)
- 테스트 없는 핵심 로직 변경
- 출처 누락 보고서 저장
- `MockLLMClient`의 silent fallback 사용

## 10. 준수 체크리스트
- [ ] Supervisor가 Preprocessing부터 최종 저장까지 제어하는가
- [ ] 세 Agent의 state가 물리적으로 분리되어 있는가
- [ ] 보고서 생성 Agent가 global_findings만 입력으로 받는가
- [ ] MaxLoop / MaxRetry / Timeout이 상수로 정의되어 있는가
- [ ] 모든 SourceDoc에 4개 메타데이터 필드가 있는가
- [ ] report_draft.status 전이가 지정된 노드에서만 발생하는가
- [ ] 보고서 목차 순서가 고정되어 있는가
- [ ] 모든 테스트가 통과하는가
