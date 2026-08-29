from langchain_core.tools import tool

from backend.chat.rag_context import record_rag_context
from backend.chat.request_context import ChatRequestContext
from backend.chat.streaming import use_request_context
from backend.rag.evidence import agent_evidence_character_budget, pack_evidence
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

        docs = rag_result.get("docs", []) if isinstance(rag_result, dict) else []
        rag_trace = rag_result.get("rag_trace", {}) if isinstance(rag_result, dict) else {}
        hitl_resume_state = (
            rag_result.get("hitl_resume_state")
            if isinstance(rag_result, dict)
            else None
        )
        ctx.store_rag_trace(rag_trace, hitl_resume_state)

        status = rag_trace.get("retrieval_status") if isinstance(rag_trace, dict) else None
        route = rag_trace.get("route") if isinstance(rag_trace, dict) else None
        if status == "needs_clarification" or route == "clarify":
            prompt = rag_trace.get("hitl_prompt") or "Please provide one more detail so I can continue."
            return f"NEEDS_CLARIFICATION: {prompt}"
        if status == "needs_scope_selection" or route == "scope_select":
            prompt = rag_trace.get("hitl_prompt") or "Please choose a knowledge-base direction."
            options = rag_trace.get("hitl_options") or []
            if options:
                prompt += "\nOptions: " + "; ".join(str(item) for item in options)
            return f"NEEDS_SCOPE_SELECTION: {prompt}"

        if not docs:
            return "No relevant documents found in the knowledge base."
        return _format_retrieved_chunks(docs)

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

    docs = rag_result.get("docs", []) if isinstance(rag_result, dict) else []
    rag_trace = rag_result.get("rag_trace", {}) if isinstance(rag_result, dict) else {}
    record_rag_context(rag_trace)

    if not docs:
        return "No relevant documents found in the knowledge base."

    return _format_retrieved_chunks(docs)
