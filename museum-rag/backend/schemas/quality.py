from typing import Literal

from pydantic import BaseModel, Field

FeedbackRating = Literal["helpful", "not_helpful"]
FeedbackReason = Literal["incorrect", "incomplete", "citation", "irrelevant", "other"]


class AnswerFeedbackRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    message_index: int = Field(ge=0)
    rating: FeedbackRating
    reason_code: FeedbackReason | None = None
    comment: str = Field(default="", max_length=500)


class AnswerFeedbackInfo(BaseModel):
    rating: FeedbackRating
    reason_code: str | None = None
    comment: str = ""
    updated_at: str


class QualityRunInfo(BaseModel):
    session_id: str
    message_index: int
    username: str
    timestamp: str
    query: str
    answer_excerpt: str
    retrieval_status: str
    retrieval_outcome: str = ""
    route: str = ""
    evidence_confidence: float | None = None
    retrieved_count: int = 0
    rerank_backend: str = ""
    rerank_applied: bool = False
    official_web_status: str = ""
    official_web_extract_status: str = ""
    official_web_extract_error_code: str = ""
    official_web_extract_duration_ms: int | None = None
    degraded_code: str = ""
    rating: FeedbackRating | None = None
    reason_code: str = ""
    comment: str = ""


class QualityMetrics(BaseModel):
    rag_answers: int = 0
    answerable_count: int = 0
    answerable_rate: float = 0
    partial_count: int = 0
    no_knowledge_count: int = 0
    degraded_count: int = 0
    web_attempt_count: int = 0
    web_success_count: int = 0
    web_extract_attempt_count: int = 0
    web_extract_success_count: int = 0
    feedback_count: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    helpful_rate: float | None = None


class QualitySummaryResponse(BaseModel):
    period_days: int
    generated_at: str
    metrics: QualityMetrics
    status_distribution: dict[str, int]
    recent_runs: list[QualityRunInfo]
    failure_queue: list[QualityRunInfo]
