from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.models import AnswerFeedback, ChatMessage, ChatSession, User
from backend.infra.database import Base
from backend.quality.service import (
    build_quality_summary,
    get_session_feedback,
    save_answer_feedback,
)
from backend.schemas.quality import AnswerFeedbackRequest


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _conversation(db):
    now = datetime.now(UTC).replace(tzinfo=None)
    user = User(username="tester", password_hash="hash", role="user")
    db.add(user)
    db.flush()
    session = ChatSession(user_id=user.id, session_id="session-1")
    db.add(session)
    db.flush()
    db.add_all(
        [
            ChatMessage(
                session_ref_id=session.id,
                message_type="human",
                content="辛追夫人的儿子是谁？",
                timestamp=now,
            ),
            ChatMessage(
                session_ref_id=session.id,
                message_type="ai",
                content="根据现有资料，相关证据仍不完整。",
                timestamp=now,
                rag_trace={
                    "retrieval_status": "partial",
                    "retrieval_outcome": "INSUFFICIENT_EVIDENCE",
                    "retrieved_chunks": [{"filename": "资料.docx", "text": "片段"}],
                },
            ),
        ]
    )
    db.commit()
    return user


def test_negative_feedback_requires_reason(db):
    user = _conversation(db)
    request = AnswerFeedbackRequest(
        session_id="session-1",
        message_index=1,
        rating="not_helpful",
    )

    with pytest.raises(HTTPException) as error:
        save_answer_feedback(db, user, request)

    assert error.value.status_code == 400
    assert db.query(AnswerFeedback).count() == 0


def test_feedback_keeps_question_answer_and_trace_snapshot(db):
    user = _conversation(db)
    result = save_answer_feedback(
        db,
        user,
        AnswerFeedbackRequest(
            session_id="session-1",
            message_index=1,
            rating="not_helpful",
            reason_code="incomplete",
            comment="缺少人物关系依据",
        ),
    )

    row = db.query(AnswerFeedback).one()
    assert result["rating"] == "not_helpful"
    assert row.query_snapshot == "辛追夫人的儿子是谁？"
    assert row.answer_snapshot.startswith("根据现有资料")
    assert row.rag_trace["retrieval_status"] == "partial"
    assert get_session_feedback(db, user.id, "session-1")[1]["reason_code"] == "incomplete"

    answer = db.query(ChatMessage).filter(ChatMessage.message_type == "ai").one()
    answer.content = "这是清空会话后生成的新回答。"
    db.commit()
    assert get_session_feedback(db, user.id, "session-1") == {}


def test_quality_summary_exposes_rates_and_failure_queue():
    runs = [
        {
            "retrieval_status": "answerable",
            "rating": "helpful",
            "official_web_status": "",
            "degraded_code": "",
        },
        {
            "retrieval_status": "partial",
            "rating": "not_helpful",
            "official_web_status": "success",
            "degraded_code": "",
        },
        {
            "retrieval_status": "no_knowledge",
            "rating": None,
            "official_web_status": "empty",
            "degraded_code": "VECTOR_TIMEOUT",
        },
    ]

    summary = build_quality_summary(runs, period_days=30, limit=10)

    assert summary["metrics"]["rag_answers"] == 3
    assert summary["metrics"]["answerable_rate"] == 0.3333
    assert summary["metrics"]["helpful_rate"] == 0.5
    assert summary["metrics"]["web_attempt_count"] == 2
    assert summary["metrics"]["degraded_count"] == 1
    assert summary["status_distribution"] == {
        "answerable": 1,
        "partial": 1,
        "no_knowledge": 1,
    }
    assert len(summary["failure_queue"]) == 2
