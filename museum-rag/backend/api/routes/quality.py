from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.db.models import User
from backend.infra.auth import get_current_user, get_db, require_admin
from backend.quality import (
    build_quality_summary,
    list_quality_runs,
    save_answer_feedback,
)
from backend.schemas import (
    AnswerFeedbackInfo,
    AnswerFeedbackRequest,
    QualitySummaryResponse,
)

router = APIRouter(prefix="/quality", tags=["quality"])


@router.post("/feedback", response_model=AnswerFeedbackInfo)
async def submit_answer_feedback(
    request: AnswerFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AnswerFeedbackInfo(**save_answer_feedback(db, current_user, request))


@router.get("/summary", response_model=QualitySummaryResponse)
async def get_quality_summary(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=30, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    runs = list_quality_runs(db, days)
    return QualitySummaryResponse(
        **build_quality_summary(runs, period_days=days, limit=limit)
    )
