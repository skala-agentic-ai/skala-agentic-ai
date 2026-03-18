# Subject

Multi-Agent 기반의 두 기업(LGES, CATL)의 전기차 캐즘 극복 전략 분석 시스템

## Overview

- **Objective** : LG에너지솔루션과 CATL의 포트폴리오 다각화 전략을 비교 분석하여, 객관적 데이터 기반의 전략 리포트를 자동 생성
- **Method** : 100페이지 분량의 전문 문서와 실시간 웹 데이터를 결합한 Agentic RAG 워크플로우를 활용
- **Tools** : LangGraph, LangChain, Python, GPT-4o-mini, FAISS, BGE-M3, SerpApi

---

## Features

- **PDF 자료 기반 정보 추출** : 기업별 리서치 자료, 기업별 사업 보고서, 배터리 시장 동향 등의 자료를 기반으로 정보 추출해 분석의 밀도를 높임
- **Supervisor 구조** : Supervisor가 보고서 생성 전과정을 책임지며, 프로그램의 흐름을 관제
- **확증 편향 방지 전략** : '강점'뿐만 아니라 '리스크'와 '한계점'을 추적하는 쌍(Pair) 쿼리를 자동 생성하여 균형 잡힌 시각을 확보
- **고밀도 RAG & 하이브리드 검색**: BGE-M3 오픈소스 임베딩을 활용해 전문 용어(4680, LFP 등)에 강한 희소 검색과 문맥 중심의 밀집 검색을 동시에 수행
- **리소스 스마트 라우팅**: 내부 문서(RAG)의 유사도 점수가 기준치(0.7) 미만일 경우, 즉시 웹 검색 에이전트를 호출하여 데이터 부족 문제를 해결
- **엄격한 품질 제어 (Self-Correction)**: 요약과 본문 수치의 일치 여부를 전수 조사하고, 출처가 누락된 데이터는 즉시 폐기하는 루프 제어 전략을 사용

---

## Tech Stack

| Category | Details |
| --- | --- |
| Framework | LangGraph, LangChain, Python |
| LLM | GPT-4o-mini |
| Retrieval | Inmemory |
| Embedding | BGE-M3 |
| Web Search | SerpApi |

---

## Agents

시스템은 **Supervisor 패턴**을 채택하여 중앙 제어자가 각 에이전트의 결과물을 검증하고 재작업을 지시함.

- **Supervisor (Orchestrator)**
    - User Query를 분석하여 편향 없는 다각도 검색 쿼리로 확장
    - 하위 에이전트들에게 업무를 배분/조율함.
    - 최종 결과물의 논리적 완결성을 검수하여 최적의 보고서를 반환함.
- **시장성 조사 Agent**
    - 글로벌 배터리 산업의 최신 트렌드, 정책 변화, 시장 규모를 조사함.
    - 특히 시장의 긍정적 전망 뒤에 숨은 리스크 요인을 발굴하여 거시적 관점의 진단을 수행함.
- **LGES Agent**
    - LG 에너지솔루션의 기술 로드맵, 공급망, 재무 건전성 등을 심층 분석함.
    - 경쟁사 대비 강점뿐만 아니라 현재 직면한 과제와 취약점을 객관적으로 파악함.
- **CATL Agent**
    - 글로벌 점유율 1위인 CATL의 시장 지배력과 lfp 등 핵심 기술력을 분석함.
    - 중국 내수 시장 외 글로벌 확장 전략과 잠재적 위협 요소를 전문적으로 추적함.
- **보고서 생성 Agent**
    - 각 에이전트의 개별 분석 데이터를 통합하여 시각화(비교표, SWOT)
    - 산업 전체 맥락에서의 종합적인 인사이트가 담긴 전문 비즈니스 보고서를 생성함.

---

## Architecture

### Agent Pattern

![image.png](https://github.com/skala-agentic-ai/skala-agentic-ai/blob/cb1ab7f51bcb062a5feb8b2d030249fda5bef8af/Agent_Pattern.png
)


### Graph

![image.png](https://github.com/skala-agentic-ai/skala-agentic-ai/blob/cb1ab7f51bcb062a5feb8b2d030249fda5bef8af/Graph.png)

---

## Directory Structure

```c
├── agents/                # Agent 모듈
├── data/                  # PDF 문서
├── docs/                  # 설계 정의 문서
├── outputs/               # 평가 결과 중간 저장
├── report/                # 최종 생성 보고서
├── retrieval/             # 검색
├── tests/                 # 테스트
├── app.py                 # 실행 스크립트
└── README.md
```

---

## Contributors

**김연수: Service Implement, Agent Design, LangGraph Design**

**장재훈: Reference Search, Agent Design, LangGraph Design**

---
