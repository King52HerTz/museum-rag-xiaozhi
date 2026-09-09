from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class StrictSchema(BaseModel):
    """接口和持久化数据使用的兼容 Schema。未知追踪字段会被忽略。"""

    model_config = ConfigDict(extra="ignore")


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default_session"


class RetrievedChunk(StrictSchema):
    filename: str
    page_number: Optional[str | int] = None
    text: Optional[str] = None
    score: Optional[float] = None
    rrf_rank: Optional[int] = None
    rerank_score: Optional[float] = None
    local_rerank_score: Optional[float] = None
    source_kind: Optional[Literal["knowledge_base", "official_web"]] = None
    source_url: Optional[str] = None


class RagTraceFields(StrictSchema):
    tool_used: Optional[bool] = None
    tool_name: Optional[str] = None
    query: Optional[str] = None
    retrieval_outcome: Optional[
        Literal["ANSWERABLE", "NO_KNOWLEDGE", "INSUFFICIENT_EVIDENCE"]
    ] = None

    # 本地现有的 Step-back / HyDE 字段
    expanded_query: Optional[str] = None
    step_back_question: Optional[str] = None
    step_back_answer: Optional[str] = None
    expansion_type: Optional[str] = None
    hypothetical_doc: Optional[str] = None

    # 上游新版的等价字段，保留以便后续流程逐步迁移
    rewrite_method: Optional[Literal["relation_expansion", "step_back", "hyde"]] = None
    rewritten_query: Optional[str] = None
    hyde_document: Optional[str] = None
    relation_candidates: Optional[List[str]] = None

    retrieval_stage: Optional[str] = None
    route: Optional[str] = None
    retrieval_status: Optional[str] = None
    grade_score: Optional[str] = None
    grade_route: Optional[str] = None
    grade_skipped: Optional[bool] = None
    rewrite_needed: Optional[bool] = None
    rewrite_strategy: Optional[str] = None
    rewrite_query: Optional[str] = None

    evidence_relevance: Optional[str] = None
    evidence_answerability: Optional[str] = None
    evidence_ambiguity: Optional[str] = None
    evidence_confidence: Optional[float] = None
    evidence_reason: Optional[str] = None
    grader_evidence_characters: Optional[int] = Field(default=None, ge=0)
    grader_evidence_omitted_count: Optional[int] = Field(default=None, ge=0)
    grader_evidence_truncated_count: Optional[int] = Field(default=None, ge=0)
    coverage_gap_codes: Optional[List[str]] = None
    coverage_gap_questions: Optional[List[str]] = None
    missing_slots: Optional[List[str]] = None
    hitl_prompt: Optional[str] = None
    hitl_options: Optional[List[str]] = None
    hitl_resumed: Optional[bool] = None
    hitl_answer: Optional[str] = None
    hitl_resume_strategy: Optional[str] = None
    hitl_resume_from_status: Optional[str] = None
    hitl_resume_from_route: Optional[str] = None

    rerank_enabled: Optional[bool] = None
    rerank_applied: Optional[bool] = None
    rerank_backend: Optional[str] = None
    rerank_model: Optional[str] = None
    rerank_endpoint: Optional[str] = None
    rerank_error: Optional[str] = None
    rerank_error_code: Optional[str] = None
    rerank_retryable: Optional[bool] = None
    rerank_timeout_seconds: Optional[float] = None
    rerank_min_score: Optional[float] = None
    rerank_semantic_weight: Optional[float] = None
    local_rerank_enabled: Optional[bool] = None
    local_rerank_applied: Optional[bool] = None
    retrieval_max_chunks_per_document: Optional[int] = None
    document_diversity_applied: Optional[bool] = None
    query_intent: Optional[str] = None
    intent_rerank_applied: Optional[bool] = None
    official_web_enabled: Optional[bool] = None
    official_web_attempted: Optional[bool] = None
    official_web_status: Optional[str] = None
    official_web_error_code: Optional[str] = None
    official_web_evidence_count: Optional[int] = None
    retrieval_boilerplate_stripped: Optional[bool] = None
    post_rerank_count: Optional[int] = None
    post_threshold_count: Optional[int] = None
    retrieval_empty: Optional[bool] = None

    retrieval_mode: Optional[str] = None
    retrieval_pipeline: Optional[str] = None
    retrieval_degraded_code: Optional[str] = None
    provider_error_code: Optional[str] = None
    provider_error_stage: Optional[str] = None
    candidate_k: Optional[int] = None
    candidate_k_source: Optional[str] = None
    candidate_k_config_error: Optional[str] = None
    retrieval_candidate_multiplier: Optional[int] = None
    retrieval_top_k: Optional[int] = None
    recall_count: Optional[int] = None
    post_merge_candidate_count: Optional[int] = None
    candidate_count: Optional[int] = None
    leaf_retrieve_level: Optional[int] = None
    auto_merge_enabled: Optional[bool] = None
    auto_merge_applied: Optional[bool] = None
    auto_merge_threshold: Optional[int] = None
    auto_merge_replaced_chunks: Optional[int] = None
    auto_merge_steps: Optional[int] = None

    retrieved_chunks: Optional[List[RetrievedChunk]] = None
    initial_retrieved_chunks: Optional[List[RetrievedChunk]] = None
    expanded_retrieved_chunks: Optional[List[RetrievedChunk]] = None
    rewrite_retrieved_chunks: Optional[List[RetrievedChunk]] = None
    hitl_targeted_retrieved_chunks: Optional[List[RetrievedChunk]] = None
    web_retrieved_chunks: Optional[List[RetrievedChunk]] = None

    complexity: Optional[str] = None
    complexity_reason: Optional[str] = None
    sub_questions: Optional[List[str]] = None
    sub_agent_count: Optional[int] = None
    synthesis_merged_count: Optional[int] = None


class RagSubTrace(RagTraceFields):
    pass


class RagTrace(RagTraceFields):
    sub_traces: Optional[List[RagSubTrace]] = None


class HitlResumeState(StrictSchema):
    """Validated snapshot used to resume a paused RAG request."""

    question: str = Field(min_length=1)
    route: Literal["clarify", "scope_select"]
    retrieval_status: Literal["needs_clarification", "needs_scope_selection"]
    rewrite_count: int = Field(default=0, ge=0)
    complexity: Optional[Literal["simple", "complex"]] = None
    complexity_reason: Optional[str] = None
    sub_questions: List[str] = Field(default_factory=list, max_length=4)


class PendingHitlState(StrictSchema):
    id: str = Field(min_length=1)
    original_question: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    options: List[str] = Field(default_factory=list)
    route: Literal["clarify", "scope_select"]
    retrieval_status: Literal["needs_clarification", "needs_scope_selection"]
    answers: List[str] = Field(default_factory=list)
    resume_state: HitlResumeState
    created_at: str


def _normalize_chunks(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    normalized = []
    for item in value:
        if isinstance(item, RetrievedChunk):
            item = item.model_dump()
        if not isinstance(item, dict) or not item.get("filename"):
            continue
        try:
            normalized.append(RetrievedChunk.model_validate(item).model_dump(exclude_none=True))
        except ValidationError:
            continue
    return normalized


def _normalize_trace_fields(trace: dict, fields: dict) -> dict:
    source = dict(trace)
    aliases = {
        "rewrite_method": "expansion_type",
        "rewritten_query": "expanded_query",
        "hyde_document": "hypothetical_doc",
    }
    for target, legacy in aliases.items():
        if target not in source and legacy in source:
            source[target] = source[legacy]

    normalized = {key: source[key] for key in fields if key in source}
    for key in (
        "retrieved_chunks",
        "initial_retrieved_chunks",
        "expanded_retrieved_chunks",
        "rewrite_retrieved_chunks",
        "hitl_targeted_retrieved_chunks",
        "web_retrieved_chunks",
    ):
        if key in normalized:
            normalized[key] = _normalize_chunks(normalized[key])
    if normalized.get("rewrite_method") not in (None, "relation_expansion", "step_back", "hyde"):
        normalized.pop("rewrite_method", None)
    return normalized


def normalize_rag_sub_trace(trace: dict | None) -> Optional[dict]:
    if not isinstance(trace, dict) or not trace:
        return None
    normalized = _normalize_trace_fields(trace, RagSubTrace.model_fields)
    try:
        return RagSubTrace.model_validate(normalized).model_dump(exclude_none=True)
    except ValidationError:
        return None


def normalize_rag_trace(trace: dict | None) -> Optional[dict]:
    """把新旧 RAG trace 统一为可安全写入数据库和返回 API 的字典。"""

    if not isinstance(trace, dict) or not trace:
        return None
    normalized = _normalize_trace_fields(trace, RagTraceFields.model_fields)
    if "sub_traces" in trace:
        sub_traces = trace["sub_traces"] if isinstance(trace["sub_traces"], list) else []
        normalized["sub_traces"] = [
            item
            for item in (
                normalize_rag_sub_trace(sub_trace)
                for sub_trace in sub_traces
                if isinstance(sub_trace, dict)
            )
            if item is not None
        ]
    try:
        return RagTrace.model_validate(normalized).model_dump(exclude_none=True)
    except ValidationError:
        return None


class ChatResponse(StrictSchema):
    response: str
    rag_trace: Optional[RagTrace] = None


class MessageInfo(StrictSchema):
    type: str
    content: str
    timestamp: str
    rag_trace: Optional[RagTrace] = None
    feedback: Optional[dict] = None


class SessionMessagesResponse(StrictSchema):
    messages: List[MessageInfo]


class SessionInfo(StrictSchema):
    session_id: str
    title: Optional[str] = None
    updated_at: str
    message_count: int


class SessionListResponse(StrictSchema):
    sessions: List[SessionInfo]


class SessionDeleteResponse(StrictSchema):
    session_id: str
    message: str
