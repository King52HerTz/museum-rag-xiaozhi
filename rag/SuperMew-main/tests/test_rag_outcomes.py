from backend.rag.outcomes import (
    RetrievalOutcome,
    outcome_for_result,
    outcome_for_status,
    partial_evidence_instruction,
    retrieval_user_message,
)


def test_status_maps_to_stable_outcomes():
    assert outcome_for_status("answerable") is RetrievalOutcome.ANSWERABLE
    assert outcome_for_status("no_knowledge") is RetrievalOutcome.NO_KNOWLEDGE
    assert outcome_for_status("partial") is RetrievalOutcome.INSUFFICIENT_EVIDENCE


def test_empty_answerable_result_is_not_reported_as_answerable():
    assert outcome_for_result(
        {"retrieval_outcome": "ANSWERABLE", "docs": []}
    ) is RetrievalOutcome.INSUFFICIENT_EVIDENCE


def test_partial_evidence_message_discloses_coverage_gaps():
    result = {
        "docs": [{"filename": "a.md"}],
        "retrieval_status": "partial",
        "coverage_gap_codes": ["MISSING_DIMENSION"],
        "coverage_gap_questions": ["还缺少哪个展柜？"],
    }
    assert outcome_for_result(result) is RetrievalOutcome.INSUFFICIENT_EVIDENCE
    message = partial_evidence_instruction(result)
    assert "MISSING_DIMENSION" in message
    assert "还缺少哪个展柜？" in message
    assert retrieval_user_message(result) is None
