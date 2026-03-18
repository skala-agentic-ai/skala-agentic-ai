# 배터리 시장 전략 분석 멀티에이전트 시스템 명세서

## 1. 시스템 개요

- **목적**: LG에너지솔루션(LGES)과 CATL의 배터리 시장 전략을 데이터 기반으로 비교 분석하여 최종 보고서를 자동 생성한다.
- **패턴**: Supervisor 패턴 (Supervisor Agent가 전체 흐름을 관장)
- **입력**: 사용자 자연어 쿼리
- **출력**: 배터리 시장 전략 분석 보고서 (.md)

---

## 2. 전체 실행 흐름
```
시작
→ 사용자 쿼리 입력
→ [Supervisor Agent 진입]
  → Preprocessing (Query Expansion → Bias Mitigation → Router)
  → Agent Execution (CATL / LGES / Market 병렬 실행)
  → Supervisor Review (GlobalConsistency → 최종 품질 검수)
    → 기준 미달: 재루프 → Agent Execution
    → 기준 충족: FinalSynth → 보고서 생성 Agent
  → 보고서 생성 Agent
  → Supervisor 최종 처리 (최종 검증 → 검증 완료 → 보고서 저장)
→ 최종 보고서 전달
```

---

## 3. 노드별 상세 명세

### 3.1 Preprocessing

**담당**: Supervisor Agent  
**목적**: 사용자 쿼리를 분석에 적합한 형태로 확장하고 편향을 완화한다.

| 단계 | 노드 | 입력 | 출력 | 설명 |
|------|------|------|------|------|
| 1 | Query Expansion | user_query | expanded_queries | 쿼리를 다각도로 확장하여 검색 커버리지를 높인다 |
| 2 | Bias Mitigation | expanded_queries | bias_queries | 긍정/부정 양방향 탐색 쿼리를 생성하여 확증 편향을 방지한다 |
| 3 | Router | bias_queries | task_routes | CATL / LGES / Market 작업을 분해하여 각 Agent에 라우팅한다 |

**State 업데이트**:
```json
{
  "global_state.user_query": "확장된 쿼리",
  "global_state.bias_queries": ["긍정 쿼리 목록", "부정 쿼리 목록"],
  "global_state.task_routes": {"catl": "...", "lges": "...", "market": "..."}
}
```

---

### 3.2 Agent Execution

**담당**: CATL Agent / LG에너지솔루션 Agent / 시장성 조사 Agent  
**목적**: 각 도메인의 증거를 수집하고 보고서에 들어갈 초안 콘텐츠를 작성한다.  
**실행 방식**: 세 Agent는 병렬로 실행된다. 각 Agent 내부 노드는 순차 처리된다.  
**루프 조건**: 보고서에 작성될 내용 평가에서 미흡 판정 시 WebSearch부터 재실행한다.

#### 3.2.1 공통 실행 순서 (CATL / LGES / Market 동일)

| 단계 | 노드 | 입력 | 출력 | 설명 |
|------|------|------|------|------|
| 1 | Web Search | task_routes | web_results | 최신 뉴스 / 기관 자료 / 보도자료 수집 |
| 2 | 논문 조사 | web_results | paper_results | Vector DB 기반 학술 문헌 검색 |
| 3 | 조사 결과 품질 평가 | web_results + paper_results | evidence_pool | 출처 신뢰성 / 최신성 / 근거 충분성 검증. 미달 시 Web Search 재실행 |
| 4 | 보고서에 들어갈 내용 작성 | evidence_pool | draft | 담당 목차 섹션 초안 작성 (아래 목차 범위 참고) |
| 5 | 보고서에 작성될 내용 평가 | draft | approved / retry_instruction | 작성된 초안의 품질 평가. 미흡 시 Web Search부터 재실행 |

#### 3.2.2 Agent별 담당 목차 범위

| Agent | 담당 목차 |
|-------|-----------|
| 시장성 조사 Agent | 1. 시장 배경 (EV 캐즘, HEV 전환, 북미 불확실성, ESS 확장, 원자재 동향) |
| LG에너지솔루션 Agent | 2. LGES 전략 분석 (2.1 핵심 전략 방향 / 2.2 KPI / 2.3 긍정 근거 / 2.4 리스크) |
| CATL Agent | 3. CATL 전략 분석 (3.1 핵심 전략 방향 / 3.2 KPI / 3.3 긍정 근거 / 3.4 리스크) |

#### 3.2.3 State 업데이트 (Agent별)
```json
{
  "market_state": {
    "evidence_pool": "수집된 증거 목록",
    "draft": "시장 배경 초안",
    "approved": true,
    "retry_instruction": "미흡 시 재시도 지시문"
  },
  "lges_state": {
    "evidence_pool": "수집된 증거 목록",
    "draft": "LGES 분석 초안",
    "approved": true,
    "retry_instruction": "미흡 시 재시도 지시문"
  },
  "catl_state": {
    "evidence_pool": "수집된 증거 목록",
    "draft": "CATL 분석 초안",
    "approved": true,
    "retry_instruction": "미흡 시 재시도 지시문"
  }
}
```

---

### 3.3 Supervisor Review

**담당**: Supervisor Agent  
**목적**: 세 Agent의 결과를 통합 검토하고 보고서 생성 가능 여부를 판단한다.  
**진입 조건**: market_state / lges_state / catl_state 모두 approved = true

| 단계 | 노드 | 입력 | 출력 | 설명 |
|------|------|------|------|------|
| 1 | GlobalConsistency 검증 | 세 Agent의 draft | consistency_report | 숫자 / 연도 / 정의 불일치 탐지. 긍정·부정 근거 균형 확인 |
| 2 | 최종 품질 검수 (분기) | consistency_report | pass / fail | 5개 품질 게이트 통과 여부 판정 |
| 3-A | Retry Instruction | fail 판정 | retry_instruction | 미흡 항목과 재시도 지시문을 생성하여 Router로 재루프 |
| 3-B | FinalSynth | pass 판정 | global_findings | 세 Agent 결과를 하나의 통합 컨텍스트로 병합 |

#### 품질 게이트 정의

| Gate | 항목 | 기준 |
|------|------|------|
| Gate 1 | 증거 충분성 | 핵심 주장마다 출처 최소 1개 이상 |
| Gate 2 | 비교 동형성 | LGES / CATL 동일 항목 기준으로 비교 가능 |
| Gate 3 | 편향 완화 | 각 기업 섹션에 반대 근거 최소 1개 이상 |
| Gate 4 | 일관성 | 숫자 / 연도 / 정의 불일치 없음 |
| Gate 5 | 포맷 완결성 | SUMMARY 최상단 / REFERENCE 최하단 / 전체 목차 존재 |

**State 업데이트**:
```json
{
  "global_state.consistency_report": "일관성 검증 결과",
  "global_state.global_findings": "통합 컨텍스트 (FinalSynth 출력)",
  "global_state.retry_instruction": "재시도 지시문 (기준 미달 시)"
}
```

---

### 3.4 보고서 생성 Agent

**담당**: 보고서 생성 Agent (독립 노드)  
**목적**: global_findings를 바탕으로 보고서 전체 구조를 생성한다.  
**진입 조건**: Supervisor Review pass → FinalSynth 완료

#### 실행 구조
```
보고서 생성 Agent
│
├── [병렬 fork]
│   ├── 핵심 전략 비교표 작성
│   ├── SWOT 그리드
│   └── 종합 시사점
│
├── [join → 병렬 fork]
│   ├── SUMMARY 생성
│   └── REFERENCE 컴파일
│
└── [join → DraftComplete]
    └── 보고서 생성 (검증 전)
```

#### 노드별 상세

| 노드 | 입력 | 출력 | 설명 |
|------|------|------|------|
| 핵심 전략 비교표 작성 | global_findings | comparison_matrix | 시장 포지셔닝 / 핵심 기술 / 수익성 / 실행력 / 주요 리스크 5개 항목 비교 |
| SWOT 그리드 | global_findings | swot | LGES / CATL 각각 S/W/O/T 작성 |
| 종합 시사점 | global_findings | implications | 분석 결론 및 전략적 시사점 도출 |
| SUMMARY 생성 | comparison_matrix + swot + implications | summary | 핵심 결론 3~5개 bullet. 0.5페이지 이내 |
| REFERENCE 컴파일 | 전체 섹션 인용 목록 | reference | 본문에서 실제 인용된 출처만 수집. 미사용 출처 제외 |
| 보고서 생성 (검증 전) | 전체 섹션 | report_draft | 전체 보고서 초안. status = pending_validation |

**State 업데이트**:
```json
{
  "report_draft": {
    "comparison_matrix": "비교표 딕셔너리",
    "swot": {"lges": {}, "catl": {}},
    "implications": "종합 시사점 텍스트",
    "summary": "SUMMARY 텍스트",
    "reference": "인용 출처 목록",
    "status": "pending_validation"
  }
}
```

---

### 3.5 Supervisor 최종 처리

**담당**: Supervisor Agent  
**목적**: 생성된 보고서 초안을 검증하고 .md 파일로 저장한다.  
**진입 조건**: report_draft.status = pending_validation

| 단계 | 노드 | 입력 | 출력 | 설명 |
|------|------|------|------|------|
| 1 | 최종 검증 | report_draft | validated / failed | 5개 품질 게이트 재확인. 포맷 완결성 검사 |
| 2-A | 검증 실패 | failed | report_draft 초기화 | 보고서 생성 Agent로 재루프. report_draft.status = failed |
| 2-B | 검증 완료 | validated | final_report | report_draft.status = validated |
| 3 | 보고서 저장 | final_report | report_path | .md 파일 저장. 파일명: report_{run_id}_{timestamp}.md |

**State 업데이트**:
```json
{
  "report_draft.status": "validated",
  "global_state.final_report": "최종 보고서 텍스트",
  "global_state.report_path": "outputs/report_{run_id}_{timestamp}.md"
}
```

---

## 4. 전체 State 스키마

### 4.1 global_state

| 필드 | 타입 | 설명 | 초기값 |
|------|------|------|--------|
| user_query | str | 확장된 사용자 쿼리 | "" |
| bias_queries | list[str] | 긍정/부정 탐색 쿼리 목록 | [] |
| task_routes | dict | Agent별 라우팅 지시 | {} |
| macro_market_context | str | 시장 배경 컨텍스트 | "" |
| global_findings | str | FinalSynth 통합 컨텍스트 | "" |
| comparison_matrix | dict | 핵심 전략 비교표 | {} |
| consistency_report | str | 일관성 검증 결과 | "" |
| retry_instruction | str | 재시도 지시문 | "" |
| final_report | str | 최종 보고서 텍스트 | "" |
| report_path | str | 저장된 파일 경로 | "" |

### 4.2 company_state (LGES / CATL / Market 각각 독립)

| 필드 | 타입 | 설명 | 초기값 |
|------|------|------|--------|
| evidence_pool | list[SourceDoc] | 수집된 증거 목록 | [] |
| draft | str | 담당 섹션 초안 | "" |
| pro_arguments | list[str] | 긍정 근거 목록 | [] |
| con_arguments | list[str] | 반대 근거 목록 | [] |
| kpi_snapshot | dict | KPI 수치 | {} |
| swot_draft | dict | SWOT 초안 | {} |
| quality_score | float | 품질 점수 | 0.0 |
| approved | bool | 승인 여부 | false |
| retry_instruction | str | 재시도 지시문 | "" |

### 4.3 report_draft

| 필드 | 타입 | 설명 | 초기값 |
|------|------|------|--------|
| summary | str | SUMMARY 섹션 | "" |
| market_background | str | 1. 시장 배경 | "" |
| lges_analysis | str | 2. LGES 전략 분석 | "" |
| catl_analysis | str | 3. CATL 전략 분석 | "" |
| comparison_matrix | dict | 4. 핵심 전략 비교표 | {} |
| swot | dict | 5. SWOT {"lges": {}, "catl": {}} | {} |
| implications | str | 6. 종합 시사점 | "" |
| reference | list[dict] | REFERENCE 목록 | [] |
| status | str | pending_validation / validated / failed | "" |

---

## 5. 제어 정책

| 상황 | 정책 | 상한 |
|------|------|------|
| Agent 내부 품질 미달 | Web Search부터 재실행 | MaxLoop = 5 |
| Supervisor Review 기준 미달 | Router부터 재루프 | MaxLoop = 5 |
| 최종 검증 실패 | 보고서 생성 Agent 재실행 | MaxRetry = 2 |
| 개별 LLM 호출 타임아웃 | 섹션 실패 마킹 후 계속 진행 | Timeout = 60s |
| 전체 타임아웃 | Force Exit. 현재까지 결과 + 한계 명시 후 종료 | Timeout = 300s |

---

## 6. 보고서 출력 목차
```
SUMMARY                     ← 0.5페이지 이내, 핵심 결론 3~5개
1. 시장 배경
2. LG에너지솔루션 전략 분석
   2.1 핵심 전략 방향
   2.2 수익성 및 KPI
   2.3 긍정 근거
   2.4 반대 근거 / 리스크
3. CATL 전략 분석
   3.1 핵심 전략 방향
   3.2 수익성 및 KPI
   3.3 긍정 근거
   3.4 반대 근거 / 리스크
4. 핵심 전략 비교
5. SWOT 분석
6. 종합 시사점
REFERENCE                   ← 실제 인용 출처만
```