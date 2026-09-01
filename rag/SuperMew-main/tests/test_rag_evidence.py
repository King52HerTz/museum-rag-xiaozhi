from unittest.mock import patch

from backend.chat import service as _chat_service  # noqa: F401
from backend.rag.evidence import pack_evidence
from backend.tools.knowledge import _format_retrieved_chunks, _render_rag_result


def _doc(name: str, text: str) -> dict:
    return {
        "filename": name,
        "page_number": 1,
        "text": text,
    }


def test_pack_evidence_keeps_complete_ranked_chunks_and_renumbers_citations():
    documents = [
        _doc("first.md", "a" * 60),
        _doc("oversized.md", "b" * 500),
        _doc("third.md", "c" * 40),
    ]

    packed = pack_evidence(documents, maximum_characters=180)

    assert len(packed.text) <= 180
    assert [item["filename"] for item in packed.documents] == [
        "first.md",
        "third.md",
    ]
    assert "[1] first.md" in packed.text
    assert "[2] third.md" in packed.text
    assert "oversized.md" not in packed.text
    assert packed.omitted_count == 1
    assert packed.truncated_count == 0


def test_pack_evidence_truncates_only_when_no_complete_chunk_can_fit():
    packed = pack_evidence(
        [_doc("large.md", "证据" * 500)],
        maximum_characters=160,
    )

    assert len(packed.text) <= 160
    assert packed.truncated_count == 1
    assert packed.omitted_count == 0
    assert "[evidence truncated by context budget]" in packed.text


def test_knowledge_tool_result_is_bounded_before_entering_agent_history():
    documents = [_doc(f"doc-{index}.md", str(index) * 900) for index in range(6)]

    with patch(
        "backend.tools.knowledge.agent_evidence_character_budget",
        return_value=1_100,
    ):
        rendered = _format_retrieved_chunks(documents)

    assert len(rendered) < 1_400
    assert "[1] doc-0.md" in rendered
    assert "doc-2.md" not in rendered
    assert "EVIDENCE_CONTEXT_NOTICE" in rendered


def test_knowledge_tool_marks_partial_evidence_without_dropping_chunks():
    rendered = _render_rag_result({
        "docs": [_doc("black-coffin.md", "黑地彩绘棺的尺寸与装饰资料")],
        "retrieval_status": "partial",
        "retrieval_outcome": "INSUFFICIENT_EVIDENCE",
        "coverage_gap_questions": ["装饰纹样是否全部有官方释义？"],
        "rag_trace": {
            "retrieval_status": "partial",
            "retrieval_outcome": "INSUFFICIENT_EVIDENCE",
        },
    })

    assert rendered.startswith("PARTIAL_EVIDENCE:")
    assert "只能回答已有证据支持的部分" in rendered
    assert "装饰纹样是否全部有官方释义" in rendered
    assert "[1] black-coffin.md" in rendered


def test_knowledge_tool_distinguishes_no_knowledge_from_insufficient_evidence():
    no_knowledge = _render_rag_result({
        "docs": [],
        "retrieval_status": "no_knowledge",
        "retrieval_outcome": "NO_KNOWLEDGE",
    })
    insufficient = _render_rag_result({
        "docs": [],
        "retrieval_status": "provider_failed",
        "retrieval_outcome": "INSUFFICIENT_EVIDENCE",
    })

    assert no_knowledge.startswith("NO_KNOWLEDGE:")
    assert insufficient.startswith("INSUFFICIENT_EVIDENCE:")
    assert "知识库中没有找到" in no_knowledge
    assert "当前证据不足" in insufficient
