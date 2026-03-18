"""State field ownership table."""

STATE_OWNERSHIP = {
    "global_state.user_query": {"QueryExpansion"},
    "global_state.bias_queries": {"BiasMitigation"},
    "global_state.task_routes": {"Router", "RetryInstruction"},
    "global_state.consistency_report": {"GlobalConsistency"},
    "global_state.global_findings": {"FinalSynth", "QualityGate"},
    "global_state.macro_market_context": {"FinalSynth"},
    "global_state.final_report": {"Formatting"},
    "global_state.report_path": {"SaveReport"},
    "market_state.approved": {"Market_ContentEval"},
    "lges_state.approved": {"LGES_ContentEval"},
    "catl_state.approved": {"CATL_ContentEval"},
    "report_draft.comparison_matrix": {"ComparisonMatrix"},
    "report_draft.swot": {"SWOTGrid"},
    "report_draft.implications": {"Implications"},
    "report_draft.summary": {"Summary"},
    "report_draft.reference": {"ReferenceCompile"},
    "report_draft.status": {"DraftComplete", "FinalValidation"},
}

SPEC_PRIORITY = {
    "state_transition": "docs/final_state_diagram.md",
    "toc_and_section_scope": "docs/final_flowchart.md",
}


def can_write(field: str, node: str) -> bool:
    owners = STATE_OWNERSHIP.get(field, set())
    return node in owners
