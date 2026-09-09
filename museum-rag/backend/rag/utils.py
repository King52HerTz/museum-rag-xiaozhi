from collections import defaultdict
from typing import List, Tuple, Dict, Any, Literal, Optional
import os
import json
import re
import requests

from backend.indexing.milvus_client import get_milvus_store
from backend.indexing.embedding import embedding_service as _embedding_service
from backend.indexing.parent_chunk_store import ParentChunkStore
from backend.infra.provider_errors import classify_provider_error
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from backend.rag.structured_output import with_structured_output


def _optional_env(name: str) -> Optional[str]:
    """Read an optional setting while treating template placeholders as unset."""
    value = (os.getenv(name) or "").strip()
    if not value:
        return None
    normalized = value.lower()
    if (
        normalized.startswith(("your_", "your-", "replace-with"))
        or "your-rerank" in normalized
        or "your_rerank" in normalized
    ):
        return None
    return value

ARK_API_KEY = os.getenv("ARK_API_KEY")
FAST_MODEL = os.getenv("FAST_MODEL")
MODEL = os.getenv("MODEL")
BASE_URL = os.getenv("BASE_URL")
RERANK_MODEL = _optional_env("RERANK_MODEL")
RERANK_BINDING_HOST = _optional_env("RERANK_BINDING_HOST")
RERANK_API_KEY = _optional_env("RERANK_API_KEY")
RERANK_ENABLED = bool(RERANK_MODEL and RERANK_API_KEY and RERANK_BINDING_HOST)
try:
    RERANK_TIMEOUT_SECONDS = max(float(os.getenv("RERANK_TIMEOUT_SECONDS", "5")), 0.1)
except ValueError:
    RERANK_TIMEOUT_SECONDS = 5.0
AUTO_MERGE_ENABLED = os.getenv("AUTO_MERGE_ENABLED", "true").lower() != "false"
AUTO_MERGE_THRESHOLD = int(os.getenv("AUTO_MERGE_THRESHOLD", "2"))
LEAF_RETRIEVE_LEVEL = int(os.getenv("LEAF_RETRIEVE_LEVEL", "3"))


def _read_positive_int_env(name: str, default: int) -> int:
    try:
        return max(int(os.getenv(name, str(default))), 1)
    except ValueError:
        return default


RETRIEVAL_CANDIDATE_MULTIPLIER = _read_positive_int_env("RETRIEVAL_CANDIDATE_MULTIPLIER", 3)
_RETRIEVAL_CANDIDATE_K_RAW = os.getenv("RETRIEVAL_CANDIDATE_K", "").strip()
RETRIEVAL_TOP_K = _read_positive_int_env("RETRIEVAL_TOP_K", 8)
LOCAL_LEXICAL_RERANK_ENABLED = os.getenv("LOCAL_LEXICAL_RERANK_ENABLED", "true").lower() != "false"
RETRIEVAL_MAX_CHUNKS_PER_DOCUMENT = _read_positive_int_env(
    "RETRIEVAL_MAX_CHUNKS_PER_DOCUMENT", 2
)


def _read_float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


RERANK_MIN_SCORE = _read_float_env("RERANK_MIN_SCORE", 0.0)

RETRIEVAL_TRACE_FIELDS = (
    "retrieval_pipeline",
    "retrieval_mode",
    "retrieval_degraded_code",
    "provider_error_code",
    "provider_error_stage",
    "candidate_k",
    "candidate_k_source",
    "candidate_k_config_error",
    "retrieval_candidate_multiplier",
    "retrieval_top_k",
    "leaf_retrieve_level",
    "recall_count",
    "post_merge_candidate_count",
    "candidate_count",
    "auto_merge_enabled",
    "auto_merge_applied",
    "auto_merge_threshold",
    "auto_merge_replaced_chunks",
    "auto_merge_steps",
    "rerank_enabled",
    "rerank_applied",
    "rerank_model",
    "rerank_endpoint",
    "rerank_error",
    "rerank_error_code",
    "rerank_retryable",
    "rerank_timeout_seconds",
    "rerank_min_score",
    "local_rerank_enabled",
    "local_rerank_applied",
    "retrieval_max_chunks_per_document",
    "document_diversity_applied",
    "post_rerank_count",
    "post_threshold_count",
    "retrieval_empty",
    "document_filter_applied",
    "document_filter_mode",
    "document_filter_count",
    "document_filter_fallback",
)

# 全局初始化检索依赖（与 api 共用 embedding_service，保证 BM25 状态一致）
_milvus_manager = get_milvus_store()
_parent_chunk_store = ParentChunkStore()

_rewrite_model = None
_stepback_model = None


def resolve_candidate_k(top_k: int) -> Tuple[int, Dict[str, Any]]:
    """解析 Milvus 候选池大小；RETRIEVAL_CANDIDATE_K 优先，否则 top_k × multiplier。"""
    if _RETRIEVAL_CANDIDATE_K_RAW:
        try:
            candidate_k = max(int(_RETRIEVAL_CANDIDATE_K_RAW), top_k)
        except ValueError:
            candidate_k = max(top_k * RETRIEVAL_CANDIDATE_MULTIPLIER, top_k)
            return candidate_k, {
                "candidate_k_source": "multiplier",
                "retrieval_candidate_multiplier": RETRIEVAL_CANDIDATE_MULTIPLIER,
                "candidate_k_config_error": "invalid RETRIEVAL_CANDIDATE_K",
            }
        return candidate_k, {
            "candidate_k_source": "env",
            "retrieval_candidate_multiplier": RETRIEVAL_CANDIDATE_MULTIPLIER,
        }
    candidate_k = max(top_k * RETRIEVAL_CANDIDATE_MULTIPLIER, top_k)
    return candidate_k, {
        "candidate_k_source": "multiplier",
        "retrieval_candidate_multiplier": RETRIEVAL_CANDIDATE_MULTIPLIER,
    }


def retrieval_trace_fields(meta: Dict[str, Any]) -> Dict[str, Any]:
    """从 retrieve meta 提取应写入 rag_trace 的检索字段。"""
    return {key: meta[key] for key in RETRIEVAL_TRACE_FIELDS if key in meta and meta[key] is not None}


def _merge_filter_expr(*parts: str) -> str:
    normalized = [part.strip() for part in parts if str(part or "").strip()]
    if not normalized:
        return ""
    return " and ".join(f"({part})" for part in normalized)


def merge_retrieval_trace(accumulated: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    """合并多路检索 trace（扩展召回）；计数类字段累加，配置类字段保留首次。"""
    incoming = retrieval_trace_fields(meta)
    if not accumulated:
        return incoming
    additive = {
        "recall_count",
        "post_merge_candidate_count",
        "auto_merge_replaced_chunks",
        "auto_merge_steps",
    }
    merged = dict(accumulated)
    for key, value in incoming.items():
        if key in additive:
            merged[key] = int(merged.get(key) or 0) + int(value or 0)
        elif key == "auto_merge_applied":
            merged[key] = bool(merged.get(key)) or bool(value)
        else:
            merged.setdefault(key, value)
    return merged


def _get_rerank_endpoint() -> str:
    if not RERANK_BINDING_HOST:
        return ""
    host = RERANK_BINDING_HOST.strip().rstrip("/")
    return host if host.endswith("/v1/rerank") else f"{host}/v1/rerank"


def _effective_score(doc: dict) -> Optional[float]:
    """精排分优先，否则用召回分；用于合并聚合与合并后重排。"""
    rerank_score = doc.get("rerank_score")
    if rerank_score is not None:
        return float(rerank_score)
    score = doc.get("score")
    if score is not None:
        return float(score)
    return None


def _meets_rerank_min_score(doc: dict) -> bool:
    score = _effective_score(doc)
    if score is None:
        return RERANK_MIN_SCORE <= 0
    return score >= RERANK_MIN_SCORE


def _merge_rank_score_into(target: dict, source: dict) -> None:
    incoming = _effective_score(source)
    if incoming is None:
        return
    uses_rerank = source.get("rerank_score") is not None or target.get("rerank_score") is not None
    if uses_rerank:
        existing = target.get("rerank_score")
        if existing is None:
            target["rerank_score"] = incoming
        else:
            target["rerank_score"] = max(float(existing), incoming)
        return
    existing = target.get("score")
    if existing is None:
        target["score"] = incoming
    else:
        target["score"] = max(float(existing), incoming)


def _merge_to_parent_level(docs: List[dict], threshold: int = 2) -> Tuple[List[dict], int]:
    groups: Dict[str, List[dict]] = defaultdict(list)
    for doc in docs:
        parent_id = (doc.get("parent_chunk_id") or "").strip()
        if parent_id:
            groups[parent_id].append(doc)

    merge_parent_ids = [parent_id for parent_id, children in groups.items() if len(children) >= threshold]
    if not merge_parent_ids:
        return docs, 0

    parent_docs = _parent_chunk_store.get_documents_by_ids(merge_parent_ids)
    parent_map = {item.get("chunk_id", ""): item for item in parent_docs if item.get("chunk_id")}

    merged_docs: List[dict] = []
    parent_slot: Dict[str, int] = {}
    merged_count = 0
    for doc in docs:
        parent_id = (doc.get("parent_chunk_id") or "").strip()
        if not parent_id or parent_id not in parent_map:
            merged_docs.append(doc)
            continue

        if parent_id in parent_slot:
            existing = merged_docs[parent_slot[parent_id]]
            _merge_rank_score_into(existing, doc)
            merged_count += 1
            continue

        parent_doc = dict(parent_map[parent_id])
        _merge_rank_score_into(parent_doc, doc)
        parent_doc["merged_from_children"] = True
        parent_doc["merged_child_count"] = len(groups[parent_id])
        parent_slot[parent_id] = len(merged_docs)
        merged_docs.append(parent_doc)
        merged_count += 1

    return merged_docs, merged_count


def _empty_merge_meta() -> Dict[str, Any]:
    return {
        "auto_merge_enabled": AUTO_MERGE_ENABLED,
        "auto_merge_applied": False,
        "auto_merge_threshold": AUTO_MERGE_THRESHOLD,
        "auto_merge_replaced_chunks": 0,
        "auto_merge_steps": 0,
        "post_merge_candidate_count": 0,
    }


def _auto_merge_candidates(docs: List[dict]) -> Tuple[List[dict], Dict[str, Any]]:
    """在完整召回候选上执行 L3→L2→L1 合并；不改变顺序，精排由后续步骤负责。"""
    meta = _empty_merge_meta()
    meta["post_merge_candidate_count"] = len(docs)
    if not AUTO_MERGE_ENABLED or not docs:
        return docs, meta

    merged_docs, merged_count_l3_l2 = _merge_to_parent_level(docs, threshold=AUTO_MERGE_THRESHOLD)
    merged_docs, merged_count_l2_l1 = _merge_to_parent_level(merged_docs, threshold=AUTO_MERGE_THRESHOLD)

    replaced_count = merged_count_l3_l2 + merged_count_l2_l1
    meta.update({
        "auto_merge_applied": replaced_count > 0,
        "auto_merge_replaced_chunks": replaced_count,
        "auto_merge_steps": int(merged_count_l3_l2 > 0) + int(merged_count_l2_l1 > 0),
        "post_merge_candidate_count": len(merged_docs),
    })
    return merged_docs, meta


def _sort_by_rank_score(docs: List[dict]) -> List[dict]:
    return sorted(docs, key=lambda item: _effective_score(item) or 0.0, reverse=True)


_QUERY_FILLERS = (
    "请介绍一下",
    "介绍一下",
    "请问",
    "能不能",
    "可以",
    "一下",
    "相关资料",
    "有关资料",
)


def _normalize_lexical_text(value: str) -> str:
    return "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", (value or "").lower()))


def _query_ngrams(query: str) -> set[str]:
    normalized = _normalize_lexical_text(query)
    for filler in _QUERY_FILLERS:
        normalized = normalized.replace(_normalize_lexical_text(filler), "")
    terms: set[str] = set()
    for size in range(2, min(4, len(normalized)) + 1):
        terms.update(normalized[index:index + size] for index in range(len(normalized) - size + 1))
    return terms


def _query_focus_terms(query: str) -> set[str]:
    """提取人物关系后的目标实体，例如“辛追的儿子利豨”中的“利豨”。"""
    normalized = _normalize_lexical_text(query)
    relation_pattern = r"(?:儿子|女儿|丈夫|妻子|父亲|母亲|墓主人|作者|主人)([\u4e00-\u9fff]{2,4})$"
    match = re.search(relation_pattern, normalized)
    return {match.group(1)} if match else set()


def _local_lexical_rerank(query: str, docs: List[dict]) -> List[dict]:
    """用精确中文实体/关系短语补强 RRF；无匹配时保持原召回顺序。"""
    terms = _query_ngrams(query)
    focus_terms = _query_focus_terms(query)
    reranked: List[dict] = []
    for index, source in enumerate(docs, 1):
        doc = dict(source)
        text = _normalize_lexical_text(str(doc.get("text") or ""))
        filename = _normalize_lexical_text(str(doc.get("filename") or ""))
        text_score = sum(len(term) ** 2 for term in terms if term in text)
        filename_score = sum(len(term) ** 2 for term in terms if term in filename)
        focus_score = sum(200 for term in focus_terms if term in text or term in filename)
        doc["local_rerank_score"] = float(text_score + filename_score * 2 + focus_score)
        doc.setdefault("rrf_rank", index)
        reranked.append(doc)
    return sorted(
        reranked,
        key=lambda item: (
            item.get("local_rerank_score", 0.0),
            -int(item.get("rrf_rank") or 0),
        ),
        reverse=True,
    )


def _prefer_document_diversity(docs: List[dict], top_k: int) -> Tuple[List[dict], bool]:
    """优先限制单文档片段数；唯一文档不足时回填，确保不损失可用结果。"""
    selected: List[dict] = []
    deferred: List[dict] = []
    counts: Dict[str, int] = defaultdict(int)
    for doc in docs:
        filename = str(doc.get("filename") or "")
        if counts[filename] < RETRIEVAL_MAX_CHUNKS_PER_DOCUMENT:
            selected.append(doc)
            counts[filename] += 1
        else:
            deferred.append(doc)
        if len(selected) >= top_k:
            break

    if len(selected) < top_k:
        selected.extend(deferred[:top_k - len(selected)])
    result = selected[:top_k]
    original = docs[:top_k]
    changed = [id(item) for item in result] != [id(item) for item in original]
    return result, changed


def dedupe_documents(docs: List[dict]) -> List[dict]:
    """按 chunk_id 去重；重复项保留更高 rank 分（rerank_score 优先）。"""
    by_key: Dict[str, dict] = {}
    order: List[str] = []
    for item in docs:
        chunk_id = (item.get("chunk_id") or "").strip()
        key = chunk_id or f"{item.get('filename')}|{item.get('page_number')}|{item.get('text')}"
        if key not in by_key:
            by_key[key] = item
            order.append(key)
            continue
        _merge_rank_score_into(by_key[key], item)
    return [by_key[key] for key in order]


def _rerank_documents(query: str, docs: List[dict], top_k: int) -> Tuple[List[dict], Dict[str, Any]]:
    docs_with_rank = [{**doc, "rrf_rank": i} for i, doc in enumerate(docs, 1)]
    meta: Dict[str, Any] = {
        "rerank_enabled": RERANK_ENABLED,
        "rerank_applied": False,
        "rerank_model": RERANK_MODEL,
        "rerank_endpoint": _get_rerank_endpoint(),
        "rerank_error": None,
        "rerank_error_code": None,
        "rerank_retryable": None,
        "rerank_timeout_seconds": RERANK_TIMEOUT_SECONDS,
        "candidate_count": len(docs_with_rank),
        "local_rerank_enabled": LOCAL_LEXICAL_RERANK_ENABLED,
        "local_rerank_applied": False,
        "retrieval_max_chunks_per_document": RETRIEVAL_MAX_CHUNKS_PER_DOCUMENT,
        "document_diversity_applied": False,
    }
    if not docs_with_rank:
        return [], meta

    def fallback() -> List[dict]:
        ranked = _sort_by_rank_score(docs_with_rank)
        if LOCAL_LEXICAL_RERANK_ENABLED:
            ranked = _local_lexical_rerank(query, ranked)
            meta["local_rerank_applied"] = True
        diversified, changed = _prefer_document_diversity(ranked, top_k)
        meta["document_diversity_applied"] = changed
        return diversified

    if not meta["rerank_enabled"]:
        return fallback(), meta

    payload = {
        "model": RERANK_MODEL,
        "query": query,
        "documents": [doc.get("text", "") for doc in docs_with_rank],
        "top_n": len(docs_with_rank),
        "return_documents": False,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RERANK_API_KEY}",
    }
    try:
        meta["rerank_applied"] = True
        response = requests.post(
            meta["rerank_endpoint"],
            headers=headers,
            json=payload,
            timeout=RERANK_TIMEOUT_SECONDS,
        )
        if response.status_code >= 400:
            public_error = classify_provider_error(
                RuntimeError(f"status code: {response.status_code}")
            )
            meta["rerank_error"] = public_error.code
            meta["rerank_error_code"] = public_error.code
            meta["rerank_retryable"] = public_error.retryable
            return fallback(), meta

        items = response.json().get("results", [])
        reranked = []
        for item in items:
            idx = item.get("index")
            if isinstance(idx, int) and 0 <= idx < len(docs_with_rank):
                doc = dict(docs_with_rank[idx])
                score = item.get("relevance_score")
                if score is not None:
                    doc["rerank_score"] = score
                reranked.append(doc)

        if reranked:
            diversified, changed = _prefer_document_diversity(reranked, top_k)
            meta["document_diversity_applied"] = changed
            return diversified, meta

        meta["rerank_error"] = "RERANK_EMPTY_RESPONSE"
        meta["rerank_error_code"] = "RERANK_EMPTY_RESPONSE"
        meta["rerank_retryable"] = False
        return fallback(), meta
    except (requests.RequestException, json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
        public_error = classify_provider_error(e)
        meta["rerank_error"] = public_error.code
        meta["rerank_error_code"] = public_error.code
        meta["rerank_retryable"] = public_error.retryable
        return fallback(), meta


class RewritePlan(BaseModel):
    method: Literal["step_back", "hyde"] = Field(
        description="本轮唯一使用的查询重写方式"
    )
    step_back_question: str = Field(
        default="",
        max_length=300,
        description="仅在 method=step_back 时填写的抽象退步问题",
    )
    hyde_document: str = Field(
        default="",
        max_length=1200,
        description="仅在 method=hyde 时填写的假设性答案文档",
    )


REWRITE_PROMPT = (
    "你是 RAG 查询重写规划器。初次检索已经找到相关信号，但证据不足。"
    "请在 step_back 和 hyde 中只选择一种重写方式，并同时生成该方式需要的内容。\n\n"
    "选择规则：\n"
    "- step_back：原问题过于具体，包含实体名、型号、时间、条件或细节，"
    "需要提升到更概括的概念、机制或原理后再检索。\n"
    "- hyde：原问题模糊、概念性强、缺少知识库常用术语，"
    "适合先生成一段可能的答案式文档，再用这段文档检索真实证据。\n\n"
    "约束：\n"
    "- method=step_back 时，只填写 step_back_question，hyde_document 必须留空。\n"
    "- method=hyde 时，只填写 hyde_document，step_back_question 必须留空。\n"
    "- HyDE 文档只能用于检索，不代表真实证据，不要编造引用或来源。\n\n"
    "用户问题：{query}"
)


def _get_rewrite_model():
    global _rewrite_model
    if not ARK_API_KEY or not FAST_MODEL:
        return None
    if _rewrite_model is None:
        _rewrite_model = init_chat_model(
            model=FAST_MODEL,
            model_provider="openai",
            api_key=ARK_API_KEY,
            base_url=BASE_URL,
            temperature=0,
            stream_usage=True,
        )
    return _rewrite_model


def rewrite_query_once(query: str) -> dict:
    """Run one structured query rewrite plan for the upgraded RAG pipeline."""
    model = _get_rewrite_model()
    if not model:
        raise RuntimeError("FAST_MODEL is required for query rewriting")

    result = with_structured_output(
        model,
        RewritePlan,
        base_url=BASE_URL,
    ).invoke(
        [{"role": "user", "content": REWRITE_PROMPT.format(query=query)}]
    )
    method = result.method
    step_back_question = (result.step_back_question or "").strip()
    hyde_document = (result.hyde_document or "").strip()

    if method == "step_back":
        if not step_back_question or hyde_document:
            raise ValueError("Step-back rewrite plan must contain only step_back_question")
        rewritten_query = f"{query}\n\n退步问题：{step_back_question}"
    elif method == "hyde":
        if not hyde_document or step_back_question:
            raise ValueError("HyDE rewrite plan must contain only hyde_document")
        rewritten_query = f"{query}\n\n假设性答案文档：{hyde_document}"
    else:
        raise ValueError(f"Unsupported rewrite method: {method}")

    return {
        "rewrite_method": method,
        "rewritten_query": rewritten_query,
        "step_back_question": step_back_question,
        "hyde_document": hyde_document,
    }


def _get_stepback_model():
    global _stepback_model
    if not ARK_API_KEY or not MODEL:
        return None
    if _stepback_model is None:
        _stepback_model = init_chat_model(
            model=MODEL,
            model_provider="openai",
            api_key=ARK_API_KEY,
            base_url=BASE_URL,
            temperature=0.2,
        )
    return _stepback_model


def _generate_step_back_question(query: str) -> str:
    model = _get_stepback_model()
    if not model:
        return ""
    prompt = (
        "请将用户的具体问题抽象成更高层次、更概括的‘退步问题’，"
        "用于探寻背后的通用原理或核心概念。只输出退步问题一句话，不要解释。\n"
        f"用户问题：{query}"
    )
    try:
        return (model.invoke(prompt).content or "").strip()
    except Exception:
        return ""


def _answer_step_back_question(step_back_question: str) -> str:
    model = _get_stepback_model()
    if not model or not step_back_question:
        return ""
    prompt = (
        "请简要回答以下退步问题，提供通用原理/背景知识，"
        "控制在120字以内。只输出答案，不要列出推理过程。\n"
        f"退步问题：{step_back_question}"
    )
    try:
        return (model.invoke(prompt).content or "").strip()
    except Exception:
        return ""


def generate_hypothetical_document(query: str) -> str:
    model = _get_stepback_model()
    if not model:
        return ""
    prompt = (
        "请基于用户问题生成一段‘假设性文档’，内容应像真实资料片段，"
        "用于帮助检索相关信息。文档可以包含合理推测，但需与问题语义相关。"
        "只输出文档正文，不要标题或解释。\n"
        f"用户问题：{query}"
    )
    try:
        return (model.invoke(prompt).content or "").strip()
    except Exception:
        return ""


def step_back_expand(query: str) -> dict:
    step_back_question = _generate_step_back_question(query)
    step_back_answer = _answer_step_back_question(step_back_question)
    if step_back_question or step_back_answer:
        expanded_query = (
            f"{query}\n\n"
            f"退步问题：{step_back_question}\n"
            f"退步问题答案：{step_back_answer}"
        )
    else:
        expanded_query = query
    return {
        "step_back_question": step_back_question,
        "step_back_answer": step_back_answer,
        "expanded_query": expanded_query,
    }


def _finalize_retrieval(
    query: str,
    retrieved: List[dict],
    top_k: int,
    retrieval_mode: str,
    candidate_k: int,
    candidate_config: Dict[str, Any],
) -> Dict[str, Any]:
    """生产流水线：召回候选 → Auto-merge → Rerank（top_k）→ 阈值过滤。"""
    candidates, merge_meta = _auto_merge_candidates(retrieved)
    reranked_docs, rerank_meta = _rerank_documents(query=query, docs=candidates, top_k=top_k)
    post_rerank_count = len(reranked_docs)
    final_docs = [d for d in reranked_docs if _meets_rerank_min_score(d)]
    meta = {
        **rerank_meta,
        **merge_meta,
        **candidate_config,
        "retrieval_mode": retrieval_mode,
        "retrieval_pipeline": "recall_merge_rerank",
        "candidate_k": candidate_k,
        "retrieval_top_k": top_k,
        "leaf_retrieve_level": LEAF_RETRIEVE_LEVEL,
        "recall_count": len(retrieved),
        "rerank_min_score": RERANK_MIN_SCORE,
        "post_rerank_count": post_rerank_count,
        "post_threshold_count": len(final_docs),
        "retrieval_empty": len(final_docs) == 0,
    }
    return {"docs": final_docs, "meta": meta}


def retrieve_documents(
    query: str,
    top_k: int = RETRIEVAL_TOP_K,
    filter_expr: str = "",
    trace_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    candidate_k, candidate_config = resolve_candidate_k(top_k)
    effective_filter_expr = _merge_filter_expr(f"chunk_level == {LEAF_RETRIEVE_LEVEL}", filter_expr)
    extra_trace = dict(trace_context or {})
    try:
        dense_embeddings = _embedding_service.get_embeddings([query])
        dense_embedding = dense_embeddings[0]
    except Exception:
        return {
            "docs": [],
            "meta": {
                "rerank_enabled": RERANK_ENABLED,
                "rerank_applied": False,
                "rerank_model": RERANK_MODEL,
                "rerank_endpoint": _get_rerank_endpoint(),
                "rerank_error": "embedding_failed",
                "rerank_timeout_seconds": RERANK_TIMEOUT_SECONDS,
                "retrieval_mode": "failed",
                "retrieval_degraded_code": "EMBEDDING_UNAVAILABLE",
                "provider_error_code": "EMBEDDING_UNAVAILABLE",
                "provider_error_stage": "embedding",
                "retrieval_pipeline": "recall_merge_rerank",
                "candidate_k": candidate_k,
                **candidate_config,
                "retrieval_top_k": top_k,
                "leaf_retrieve_level": LEAF_RETRIEVE_LEVEL,
                "recall_count": 0,
                **_empty_merge_meta(),
                "candidate_count": 0,
                "rerank_min_score": RERANK_MIN_SCORE,
                "post_rerank_count": 0,
                "post_threshold_count": 0,
                "retrieval_empty": True,
                **extra_trace,
            },
        }

    try:
        retrieved = _milvus_manager.hybrid_retrieve(
            dense_embedding=dense_embedding,
            query=query,
            top_k=candidate_k,
            filter_expr=effective_filter_expr,
        )
        result = _finalize_retrieval(
            query=query,
            retrieved=retrieved,
            top_k=top_k,
            retrieval_mode="hybrid",
            candidate_k=candidate_k,
            candidate_config=candidate_config,
        )
        result["meta"].update(extra_trace)
        return result
    except Exception:
        try:
            retrieved = _milvus_manager.dense_retrieve(
                dense_embedding=dense_embedding,
                top_k=candidate_k,
                filter_expr=effective_filter_expr,
            )
            result = _finalize_retrieval(
                query=query,
                retrieved=retrieved,
                top_k=top_k,
                retrieval_mode="dense_fallback",
                candidate_k=candidate_k,
                candidate_config=candidate_config,
            )
            result["meta"]["retrieval_degraded_code"] = "HYBRID_RETRIEVAL_FALLBACK"
            result["meta"].update(extra_trace)
            return result
        except Exception:
            return {
                "docs": [],
                "meta": {
                    "rerank_enabled": RERANK_ENABLED,
                    "rerank_applied": False,
                    "rerank_model": RERANK_MODEL,
                    "rerank_endpoint": _get_rerank_endpoint(),
                    "rerank_error": "retrieve_failed",
                    "rerank_timeout_seconds": RERANK_TIMEOUT_SECONDS,
                    "retrieval_mode": "failed",
                    "retrieval_degraded_code": "VECTOR_STORE_UNAVAILABLE",
                    "provider_error_code": "VECTOR_STORE_UNAVAILABLE",
                    "provider_error_stage": "retrieval",
                    "retrieval_pipeline": "recall_merge_rerank",
                    "candidate_k": candidate_k,
                    **candidate_config,
                    "retrieval_top_k": top_k,
                    "leaf_retrieve_level": LEAF_RETRIEVE_LEVEL,
                    "recall_count": 0,
                    **_empty_merge_meta(),
                    "candidate_count": 0,
                    "rerank_min_score": RERANK_MIN_SCORE,
                    "post_rerank_count": 0,
                    "post_threshold_count": 0,
                    "retrieval_empty": True,
                    **extra_trace,
                },
            }
