import logging
import time
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.resources import document_profile_store
from backend.infra.auth import verify_bridge_api_key
from backend.rag.utils import retrieve_documents, retrieval_trace_fields

router = APIRouter(prefix="/api/museum", tags=["museum"])
logger = logging.getLogger("museum.bridge")


class MuseumQueryRequest(BaseModel):
    question: str = Field(..., description="游客提出的展品、文物或导览相关问题")
    museum: Optional[str] = Field(default="湖南省博物馆", description="博物馆名称")
    exhibition: Optional[str] = Field(default=None, description="展览名称")
    exhibit_id: Optional[str] = Field(default=None, description="可选展品编号")
    era: Optional[str] = Field(default=None, description="可选时代标签")
    category: Optional[str] = Field(default=None, description="可选类别标签")
    scene: Optional[str] = Field(default="museum_guide", description="调用场景")
    top_k: int = Field(default=5, ge=1, le=10, description="返回片段数量")
    need_trace: bool = Field(default=True, description="是否返回检索 trace")


class MuseumContext(BaseModel):
    index: int
    content: str
    source: str
    title: Optional[str] = None
    page_number: Optional[str | int] = None
    score: Optional[float] = None
    rerank_score: Optional[float] = None
    chunk_id: Optional[str] = None


class MuseumQueryResponse(BaseModel):
    code: int
    message: str
    query: str = ""
    contexts: List[MuseumContext] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    details: List[str] = Field(default_factory=list)


def _build_response(
    *,
    code: int,
    message: str,
    query: str = "",
    contexts: Optional[List[MuseumContext]] = None,
    trace: Optional[dict[str, Any]] = None,
    error_code: Optional[str] = None,
    details: Optional[List[str]] = None,
) -> MuseumQueryResponse:
    return MuseumQueryResponse(
        code=code,
        message=message,
        query=query,
        contexts=contexts or [],
        trace=trace or {},
        error_code=error_code,
        details=details or [],
    )


def _build_retrieval_query(request: MuseumQueryRequest) -> str:
    """把业务上下文合入检索问题，作为结构化过滤的语义补充。"""
    parts: list[str] = []
    if request.museum:
        parts.append(f"博物馆：{request.museum}")
    if request.exhibition:
        parts.append(f"展览：{request.exhibition}")
    if request.exhibit_id:
        parts.append(f"展品编号：{request.exhibit_id}")
    if request.era:
        parts.append(f"时代：{request.era}")
    if request.category:
        parts.append(f"类别：{request.category}")
    parts.append(f"游客问题：{request.question}")
    return "\n".join(parts)


def _to_context(index: int, doc: dict) -> MuseumContext:
    source = str(doc.get("filename") or doc.get("source") or "Unknown")
    content = str(doc.get("text") or doc.get("content") or "").strip()
    return MuseumContext(
        index=index,
        content=content,
        source=source,
        title=source,
        page_number=doc.get("page_number"),
        score=doc.get("score"),
        rerank_score=doc.get("rerank_score"),
        chunk_id=doc.get("chunk_id"),
    )


def _trace_summary(trace: dict[str, Any]) -> str:
    if not trace:
        return "retrieval_mode=-|retrieval_empty=-|rerank_error=-"
    rerank_error = "yes" if trace.get("rerank_error") else "no"
    retrieval_mode = trace.get("retrieval_mode") or "-"
    retrieval_empty = trace.get("retrieval_empty")
    return (
        f"retrieval_mode={retrieval_mode}"
        f"|retrieval_empty={retrieval_empty if retrieval_empty is not None else '-'}"
        f"|rerank_error={rerank_error}"
    )


def _question_preview(question: str, limit: int = 48) -> str:
    text = str(question or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _quote_milvus_string(value: str) -> str:
    text = str(value or "").replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _build_filename_filter(filenames: list[str]) -> str:
    quoted = [_quote_milvus_string(name) for name in filenames if str(name or "").strip()]
    if not quoted:
        return ""
    return f"filename in [{', '.join(quoted)}]"


def _build_filter_trace(
    *,
    request: MuseumQueryRequest,
    matched_filenames: list[str],
    filter_mode: str,
    fallback: str = "none",
) -> dict[str, Any]:
    has_structured_filter = any(
        [
            request.museum,
            request.exhibition,
            request.exhibit_id,
            request.era,
            request.category,
        ]
    )
    return {
        "document_filter_applied": bool(matched_filenames),
        "document_filter_mode": filter_mode if has_structured_filter else "none",
        "document_filter_count": len(matched_filenames),
        "document_filter_fallback": fallback,
    }


@router.post("/query", response_model=MuseumQueryResponse)
async def museum_query(
    http_request: Request,
    request: MuseumQueryRequest,
    _: None = Depends(verify_bridge_api_key),
):
    """给小智服务端调用的轻量检索型接口。

    只复用 SuperMew RAG 的 hybrid recall / auto-merge / rerank 检索能力，
    返回证据片段；不在本接口生成最终导览话术，最终回答由小智服务端根据
    contexts 交给 LLM 生成。
    """
    query = ""
    trace: dict[str, Any] = {}
    trace_id = str(getattr(http_request.state, "bridge_trace_id", "") or http_request.headers.get("X-Bridge-Trace-Id") or "").strip()
    started_at = time.perf_counter()
    logger.info(
        "museum bridge request | trace_id=%s | museum=%s | exhibition=%s | exhibit_id=%s | era=%s | category=%s | top_k=%s | need_trace=%s | question_len=%s | question=%s",
        trace_id or "-",
        request.museum or "-",
        request.exhibition or "-",
        request.exhibit_id or "-",
        request.era or "-",
        request.category or "-",
        request.top_k,
        request.need_trace,
        len(request.question or ""),
        _question_preview(request.question),
    )
    try:
        query = _build_retrieval_query(request)
        matched_filenames = document_profile_store.find_filenames(
            museum=request.museum or "",
            exhibition=request.exhibition or "",
            exhibit_id=request.exhibit_id or "",
            era=request.era or "",
            category=request.category or "",
        )
        filename_filter_expr = _build_filename_filter(matched_filenames)
        result = retrieve_documents(
            query,
            top_k=request.top_k,
            filter_expr=filename_filter_expr,
            trace_context=_build_filter_trace(
                request=request,
                matched_filenames=matched_filenames,
                filter_mode="structured" if filename_filter_expr else "semantic_only",
            ),
        )
        docs = result.get("docs", []) if isinstance(result, dict) else []
        if not docs and filename_filter_expr:
            result = retrieve_documents(
                query,
                top_k=request.top_k,
                trace_context=_build_filter_trace(
                    request=request,
                    matched_filenames=matched_filenames,
                    filter_mode="structured_with_fallback",
                    fallback="semantic_only",
                ),
            )
            docs = result.get("docs", []) if isinstance(result, dict) else []
        contexts = [
            _to_context(index, doc)
            for index, doc in enumerate(docs[: request.top_k], start=1)
            if (doc.get("text") or doc.get("content"))
        ]
        meta = result.get("meta", {}) if isinstance(result, dict) else {}
        trace = retrieval_trace_fields(meta) if isinstance(meta, dict) else {}

        if not contexts:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(
                "museum bridge empty result | trace_id=%s | elapsed_ms=%s | contexts=%s | %s",
                trace_id or "-",
                elapsed_ms,
                0,
                _trace_summary(trace),
            )
            return _build_response(
                code=0,
                message="未检索到相关资料",
                query=query,
                contexts=[],
                trace=trace if request.need_trace else {},
            )

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.info(
            "museum bridge success | trace_id=%s | elapsed_ms=%s | contexts=%s | %s",
            trace_id or "-",
            elapsed_ms,
            len(contexts),
            _trace_summary(trace),
        )
        return _build_response(
            code=0,
            message="检索成功",
            query=query,
            contexts=contexts,
            trace=trace if request.need_trace else {},
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        logger.exception(
            "museum bridge query failed | trace_id=%s | elapsed_ms=%s | error_type=%s",
            trace_id or "-",
            elapsed_ms,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "code": 50001,
                "message": "博物馆知识库检索失败",
                "query": query,
                "contexts": [],
                "trace": trace if request.need_trace else {},
                "error_code": "MUSEUM_QUERY_FAILED",
                "details": [str(exc)],
            },
        ) from exc
