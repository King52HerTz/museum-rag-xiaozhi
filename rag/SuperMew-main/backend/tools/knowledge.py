from langchain_core.tools import tool

from backend.chat.rag_context import record_rag_context
from backend.chat.request_context import ChatRequestContext
from backend.chat.streaming import use_request_context
from backend.rag.evidence import agent_evidence_character_budget, pack_evidence
from backend.rag.outcomes import (
    RetrievalOutcome,
    outcome_for_result,
    partial_evidence_instruction,
    retrieval_user_message,
)
from backend.rag.pipeline import run_rag_graph

_KNOWLEDGE_TOOL_CALLS_THIS_TURN = 0


def reset_knowledge_tool_calls() -> None:
    """每轮对话开始时重置知识库工具调用计数。"""
    global _KNOWLEDGE_TOOL_CALLS_THIS_TURN
    _KNOWLEDGE_TOOL_CALLS_THIS_TURN = 0


def _try_acquire_knowledge_tool_call() -> bool:
    global _KNOWLEDGE_TOOL_CALLS_THIS_TURN
    if _KNOWLEDGE_TOOL_CALLS_THIS_TURN >= 1:
        return False
    _KNOWLEDGE_TOOL_CALLS_THIS_TURN += 1
    return True


def _format_retrieved_chunks(docs: list[dict]) -> str:
    evidence = pack_evidence(
        docs,
        maximum_characters=agent_evidence_character_budget(),
    )
    budget_notice = ""
    if evidence.omitted_count or evidence.truncated_count:
        budget_notice = (
            "\nEVIDENCE_CONTEXT_NOTICE: Only the shown highest-ranked chunks fit "
            "the answer context. Use only these chunks."
        )
    return "Retrieved Chunks:\n" + evidence.text + budget_notice


def _render_rag_result(rag_result: dict) -> str:
    docs = rag_result.get("docs") or []
    rag_trace = rag_result.get("rag_trace") or {}
    status = rag_result.get("retrieval_status") or rag_trace.get("retrieval_status")
    route = rag_result.get("route") or rag_trace.get("route")

    if status == "needs_clarification" or route == "clarify":
        prompt = rag_trace.get("hitl_prompt") or (
            "Please provide one more detail so I can continue."
        )
        return f"NEEDS_CLARIFICATION: {prompt}"
    if status == "needs_scope_selection" or route == "scope_select":
        prompt = rag_trace.get("hitl_prompt") or "Please choose a knowledge-base direction."
        options = rag_trace.get("hitl_options") or []
        if options:
            prompt += "\nOptions: " + "; ".join(str(item) for item in options)
        return f"NEEDS_SCOPE_SELECTION: {prompt}"

    outcome = outcome_for_result(rag_result)
    if not docs:
        message = retrieval_user_message(rag_result) or "当前没有可用于回答的可靠证据。"
        marker = (
            "NO_KNOWLEDGE"
            if outcome == RetrievalOutcome.NO_KNOWLEDGE
            else "INSUFFICIENT_EVIDENCE"
        )
        return f"{marker}: {message}"

    chunks = _format_retrieved_chunks(docs)
    if outcome == RetrievalOutcome.INSUFFICIENT_EVIDENCE:
        instruction = partial_evidence_instruction(rag_result)
        return f"PARTIAL_EVIDENCE: {instruction}\n{chunks}"
    return chunks


def make_search_knowledge_base(ctx: ChatRequestContext):
    """创建绑定到单次请求上下文的知识库工具。"""

    @tool("search_knowledge_base")
    def search_knowledge_base_for_request(query: str) -> str:
        """Search for information in the knowledge base using hybrid retrieval."""
        if not ctx.acquire_knowledge_tool_slot():
            return (
                "TOOL_CALL_LIMIT_REACHED: search_knowledge_base has already been called once in this turn. "
                "Use the existing retrieval result and provide the final answer directly."
            )

        with use_request_context(ctx):
            rag_result = run_rag_graph(query, ctx)

        rag_trace = rag_result.get("rag_trace", {}) if isinstance(rag_result, dict) else {}
        hitl_resume_state = (
            rag_result.get("hitl_resume_state")
            if isinstance(rag_result, dict)
            else None
        )
        ctx.store_rag_trace(rag_trace, hitl_resume_state)

        return _render_rag_result(rag_result)

    return search_knowledge_base_for_request


@tool("search_knowledge_base")
def search_knowledge_base(query: str) -> str:
    """Search for information in the knowledge base using hybrid retrieval (dense + sparse vectors)."""
    if not _try_acquire_knowledge_tool_call():
        return (
            "TOOL_CALL_LIMIT_REACHED: search_knowledge_base has already been called once in this turn. "
            "Use the existing retrieval result and provide the final answer directly."
        )

    rag_result = run_rag_graph(query)

    rag_trace = rag_result.get("rag_trace", {}) if isinstance(rag_result, dict) else {}
    record_rag_context(rag_trace)

    return _render_rag_result(rag_result)
