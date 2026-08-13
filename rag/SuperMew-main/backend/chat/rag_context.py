"""单轮对话内 RAG trace 暂存（工具执行 → 流式结束后写入会话）。"""

from typing import Optional

from backend.chat.streaming import get_request_context
from backend.schemas.chat import normalize_rag_trace

_LAST_RAG_CONTEXT: Optional[dict] = None


def get_last_rag_context(clear: bool = True) -> Optional[dict]:
    """获取最近一次 RAG 检索上下文，默认读取后清空。"""
    request_context = get_request_context()
    if request_context is not None:
        return request_context.take_rag_trace() if clear else request_context.peek_rag_trace()

    global _LAST_RAG_CONTEXT
    context = _LAST_RAG_CONTEXT
    if clear:
        _LAST_RAG_CONTEXT = None
    return context


def record_rag_context(rag_trace: dict) -> None:
    normalized_trace = normalize_rag_trace(rag_trace)
    if normalized_trace:
        request_context = get_request_context()
        if request_context is not None:
            request_context.store_rag_trace(normalized_trace)
            return

        global _LAST_RAG_CONTEXT
        _LAST_RAG_CONTEXT = {"rag_trace": normalized_trace}
