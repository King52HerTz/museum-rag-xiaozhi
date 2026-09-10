from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.db.models import AnswerFeedback, ChatMessage, ChatSession, User
from backend.schemas.chat import normalize_rag_trace
from backend.schemas.quality import AnswerFeedbackRequest


def _excerpt(value: str, maximum: int = 240) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= maximum else f"{text[:maximum]}…"


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _feedback_dict(row: AnswerFeedback) -> dict:
    return {
        "rating": row.rating,
        "reason_code": row.reason_code or None,
        "comment": row.comment or "",
        "updated_at": row.updated_at.isoformat(),
    }


def get_session_feedback(db: Session, user_id: int, session_id: str) -> dict[int, dict]:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id, ChatSession.session_id == session_id)
        .first()
    )
    if not session:
        return {}
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_ref_id == session.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    rows = (
        db.query(AnswerFeedback)
        .filter(
            AnswerFeedback.user_id == user_id,
            AnswerFeedback.session_id == session_id,
        )
        .all()
    )
    return {
        row.message_index: _feedback_dict(row)
        for row in rows
        if row.message_index < len(messages)
        and row.answer_snapshot == messages[row.message_index].content
    }


def save_answer_feedback(
    db: Session,
    user: User,
    request: AnswerFeedbackRequest,
) -> dict:
    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id == user.id,
            ChatSession.session_id == request.session_id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_ref_id == session.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    if request.message_index >= len(messages):
        raise HTTPException(status_code=404, detail="回答不存在")
    target = messages[request.message_index]
    if target.message_type != "ai":
        raise HTTPException(status_code=400, detail="只能评价助手回答")
    if request.rating == "not_helpful" and not request.reason_code:
        raise HTTPException(status_code=400, detail="请选择需要改进的原因")

    query = ""
    for index in range(request.message_index - 1, -1, -1):
        if messages[index].message_type == "human":
            query = messages[index].content
            break

    feedback = (
        db.query(AnswerFeedback)
        .filter(
            AnswerFeedback.user_id == user.id,
            AnswerFeedback.session_id == request.session_id,
            AnswerFeedback.message_index == request.message_index,
        )
        .first()
    )
    now = _utcnow_naive()
    if not feedback:
        feedback = AnswerFeedback(
            user_id=user.id,
            session_id=request.session_id,
            message_index=request.message_index,
            created_at=now,
        )
        db.add(feedback)

    feedback.rating = request.rating
    feedback.reason_code = request.reason_code or ""
    feedback.comment = request.comment.strip()
    feedback.query_snapshot = query
    feedback.answer_snapshot = target.content
    feedback.rag_trace = normalize_rag_trace(target.rag_trace)
    feedback.updated_at = now
    db.commit()
    db.refresh(feedback)
    return _feedback_dict(feedback)


def list_quality_runs(db: Session, period_days: int) -> list[dict]:
    since = _utcnow_naive() - timedelta(days=period_days)
    sessions = (
        db.query(ChatSession, User)
        .join(User, ChatSession.user_id == User.id)
        .filter(ChatSession.updated_at >= since)
        .all()
    )
    feedback_rows = db.query(AnswerFeedback).filter(AnswerFeedback.updated_at >= since).all()
    feedback_map = {
        (row.user_id, row.session_id, row.message_index): row for row in feedback_rows
    }

    runs: list[dict] = []
    for session, user in sessions:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_ref_id == session.id)
            .order_by(ChatMessage.id.asc())
            .all()
        )
        latest_query = ""
        for message_index, message in enumerate(messages):
            if message.message_type == "human":
                latest_query = message.content
                continue
            trace = normalize_rag_trace(message.rag_trace)
            if message.message_type != "ai" or not trace or message.timestamp < since:
                continue
            feedback = feedback_map.get((user.id, session.session_id, message_index))
            if feedback and feedback.answer_snapshot != message.content:
                feedback = None
            chunks = trace.get("retrieved_chunks") or []
            runs.append(
                {
                    "session_id": session.session_id,
                    "message_index": message_index,
                    "username": user.username,
                    "timestamp": message.timestamp.isoformat(),
                    "query": _excerpt(latest_query),
                    "answer_excerpt": _excerpt(message.content),
                    "retrieval_status": str(trace.get("retrieval_status") or "unknown"),
                    "retrieval_outcome": str(trace.get("retrieval_outcome") or ""),
                    "route": str(trace.get("route") or ""),
                    "evidence_confidence": trace.get("evidence_confidence"),
                    "retrieved_count": len(chunks),
                    "rerank_backend": str(trace.get("rerank_backend") or ""),
                    "rerank_applied": bool(trace.get("rerank_applied")),
                    "official_web_status": str(trace.get("official_web_status") or ""),
                    "official_web_extract_status": str(
                        trace.get("official_web_extract_status") or ""
                    ),
                    "official_web_extract_error_code": str(
                        trace.get("official_web_extract_error_code") or ""
                    ),
                    "official_web_extract_duration_ms": trace.get(
                        "official_web_extract_duration_ms"
                    ),
                    "degraded_code": str(
                        trace.get("retrieval_degraded_code")
                        or trace.get("provider_error_code")
                        or ""
                    ),
                    "rating": feedback.rating if feedback else None,
                    "reason_code": feedback.reason_code if feedback else "",
                    "comment": feedback.comment if feedback else "",
                }
            )
    return sorted(runs, key=lambda item: item["timestamp"], reverse=True)


def build_quality_summary(
    runs: list[dict],
    *,
    period_days: int,
    limit: int,
) -> dict:
    statuses = Counter(str(run.get("retrieval_status") or "unknown") for run in runs)
    rag_answers = len(runs)
    answerable_count = statuses.get("answerable", 0)
    helpful_count = sum(run.get("rating") == "helpful" for run in runs)
    not_helpful_count = sum(run.get("rating") == "not_helpful" for run in runs)
    feedback_count = helpful_count + not_helpful_count
    web_attempt_count = sum(bool(run.get("official_web_status")) for run in runs)
    web_success_count = sum(run.get("official_web_status") == "success" for run in runs)
    web_extract_attempt_count = sum(
        bool(run.get("official_web_extract_status")) for run in runs
    )
    web_extract_success_count = sum(
        run.get("official_web_extract_status") == "success" for run in runs
    )
    failures = [
        run
        for run in runs
        if run.get("rating") == "not_helpful"
        or run.get("retrieval_status") != "answerable"
        or bool(run.get("degraded_code"))
    ]
    return {
        "period_days": period_days,
        "generated_at": datetime.now(UTC).isoformat(),
        "metrics": {
            "rag_answers": rag_answers,
            "answerable_count": answerable_count,
            "answerable_rate": round(answerable_count / rag_answers, 4) if rag_answers else 0,
            "partial_count": statuses.get("partial", 0),
            "no_knowledge_count": statuses.get("no_knowledge", 0),
            "degraded_count": sum(bool(run.get("degraded_code")) for run in runs),
            "web_attempt_count": web_attempt_count,
            "web_success_count": web_success_count,
            "web_extract_attempt_count": web_extract_attempt_count,
            "web_extract_success_count": web_extract_success_count,
            "feedback_count": feedback_count,
            "helpful_count": helpful_count,
            "not_helpful_count": not_helpful_count,
            "helpful_rate": (
                round(helpful_count / feedback_count, 4) if feedback_count else None
            ),
        },
        "status_distribution": dict(statuses),
        "recent_runs": runs[:limit],
        "failure_queue": failures[:limit],
    }
