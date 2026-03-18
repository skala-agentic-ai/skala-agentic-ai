stateDiagram-v2
  [*] --> Idle

  Idle --> Preprocessing : 사용자 쿼리 수신

  state Preprocessing {
    [*] --> QueryExpansion
    QueryExpansion --> BiasMitigation : 쿼리 확장 완료\nglobal_state.user_query 업데이트
    BiasMitigation --> Routing : 반대 쿼리 생성 완료\nglobal_state.bias_queries 업데이트
    Routing --> [*] : 작업 분해 완료\nglobal_state.task_routes 업데이트
  }

  Preprocessing --> AgentExecution : 전처리 완료

  state AgentExecution {

    state MarketLoop {
      [*] --> Market_WebSearch
      Market_WebSearch --> Market_PaperSearch : web 결과 수집
      Market_PaperSearch --> Market_QualityCheck : 논문 수집
      Market_QualityCheck --> Market_WriteContent : 품질 통과\nmarket_state.evidence_pool 업데이트
      Market_QualityCheck --> Market_WebSearch : 품질 미달\n재수집
      Market_WriteContent --> Market_ContentEval : 시장 배경 초안 작성\nmarket_state.draft 업데이트
      Market_ContentEval --> [*] : 승인\nmarket_state.approved = true
      Market_ContentEval --> Market_WebSearch : 미흡\nmarket_state.retry_instruction 업데이트
    }

    state LGESLoop {
      [*] --> LGES_WebSearch
      LGES_WebSearch --> LGES_PaperSearch : web 결과 수집
      LGES_PaperSearch --> LGES_QualityCheck : 논문 수집
      LGES_QualityCheck --> LGES_WriteContent : 품질 통과\nlges_state.evidence_pool 업데이트
      LGES_QualityCheck --> LGES_WebSearch : 품질 미달\n재수집
      LGES_WriteContent --> LGES_ContentEval : 목차 3·4·5·6 초안 작성\nlges_state.draft 업데이트
      LGES_ContentEval --> [*] : 승인\nlges_state.approved = true
      LGES_ContentEval --> LGES_WebSearch : 미흡\nlges_state.retry_instruction 업데이트
    }

    state CATLLoop {
      [*] --> CATL_WebSearch
      CATL_WebSearch --> CATL_PaperSearch : web 결과 수집
      CATL_PaperSearch --> CATL_QualityCheck : 논문 수집
      CATL_QualityCheck --> CATL_WriteContent : 품질 통과\ncatl_state.evidence_pool 업데이트
      CATL_QualityCheck --> CATL_WebSearch : 품질 미달\n재수집
      CATL_WriteContent --> CATL_ContentEval : 목차 3·4·5·6 초안 작성\ncatl_state.draft 업데이트
      CATL_ContentEval --> [*] : 승인\ncatl_state.approved = true
      CATL_ContentEval --> CATL_WebSearch : 미흡\ncatl_state.retry_instruction 업데이트
    }

  }

  AgentExecution --> SupervisorReview : 전 에이전트 승인 완료\nmarket/lges/catl_state.approved = true

  state SupervisorReview {
    [*] --> GlobalConsistency
    GlobalConsistency --> QualityGate : 일관성 검증 완료\nglobal_state.consistency_report 업데이트
    QualityGate --> ReadyToWrite : 기준 충족\nglobal_state.global_findings 업데이트
    QualityGate --> RetryInstruction : 기준 미달\nglobal_state.retry_instruction 업데이트
    RetryInstruction --> [*] : 재루프 지시\nglobal_state.task_routes 재설정
    ReadyToWrite --> [*] : 보고서 생성 Agent로 전달
  }

  SupervisorReview --> AgentExecution : 재루프\nglobal_state.retry_instruction 존재
  SupervisorReview --> ReportWriter : 기준 충족

  state ReportWriter {

    [*] --> fork1
    state fork1 <<fork>>

    fork1 --> ComparisonMatrix
    fork1 --> SWOTGrid
    fork1 --> Implications

    ComparisonMatrix --> join1 : 비교표 완성\nreport_draft.comparison_matrix 업데이트
    SWOTGrid --> join1 : SWOT 완성\nreport_draft.swot 업데이트
    Implications --> join1 : 시사점 완성\nreport_draft.implications 업데이트

    state join1 <<join>>

    join1 --> fork2
    state fork2 <<fork>>

    fork2 --> Summary
    fork2 --> ReferenceCompile

    Summary --> join2 : SUMMARY 완성\nreport_draft.summary 업데이트
    ReferenceCompile --> join2 : REFERENCE 완성\nreport_draft.reference 업데이트

    state join2 <<join>>

    join2 --> DraftComplete : 초안 완성\nreport_draft.status = pending_validation

    DraftComplete --> [*]
  }

  ReportWriter --> FinalOutput : 보고서 초안 완성

  state FinalOutput {
    [*] --> FinalValidation
    FinalValidation --> Formatting : 검증 통과\nreport_draft.status = validated
    FinalValidation --> ValidationFailed : 검증 실패\nreport_draft.status = failed
    ValidationFailed --> [*] : 재생성 지시\nreport_draft 초기화
    Formatting --> SaveReport : .md 렌더링 완료\nglobal_state.final_report 업데이트
    SaveReport --> [*] : 저장 완료\nglobal_state.report_path 업데이트
  }

  FinalOutput --> ReportWriter : 검증 실패\n재생성
  FinalOutput --> [*] : 보고서 전달 완료