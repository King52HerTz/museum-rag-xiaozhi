from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.routes import auth, chat, sessions
from backend.chat import storage
from backend.db.models import ChatSession, MobileTaskCompletion, User
from backend.infra.auth import get_current_user, get_db
from backend.infra.cache import cache
from backend.schemas import AuthResponse, ChatRequest, ChatResponse, RegisterRequest, SessionInfo, SessionListResponse
from backend.schemas.mobile import Audience, MobileChatRequest, MobileRegisterRequest, MobileSessionRequest
from backend.schemas.mobile import MobileProgressRequest, MobileProgressResponse

router = APIRouter(prefix="/mobile", tags=["mobile"])

TASK_IDS = {"clothes-light-v1", "clothes-pattern-v1"}


def _progress(db: Session, user: User, audience: Audience):
    tasks = {row.task_id for row in db.query(MobileTaskCompletion).filter_by(
        user_id=user.id, audience=audience).all()} & TASK_IDS
    return MobileProgressResponse(audience=audience, completed_tasks=sorted(tasks),
                                  rewards=["clothes-journal-v1"] if tasks == TASK_IDS else [])


@router.get("/progress", response_model=MobileProgressResponse)
async def get_progress(audience: Audience, current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    return _progress(db, current_user, audience)


@router.post("/progress/sync", response_model=MobileProgressResponse)
async def sync_progress(request: MobileProgressRequest,
                        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # The unique key makes overlapping retries safe; completion is a grow-only set.
    if db.get_bind().dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    for task_id in set(request.completed_tasks):
        statement = insert(MobileTaskCompletion).values(
            user_id=current_user.id, audience=request.audience, task_id=task_id
        ).on_conflict_do_nothing(index_elements=["user_id", "audience", "task_id"])
        db.execute(statement)
    db.commit()
    return _progress(db, current_user, request.audience)


def _owned_session(db: Session, user: User, session_id: str, audience: Audience):
    session = db.query(ChatSession).filter(
        ChatSession.user_id == user.id, ChatSession.session_id == session_id
    ).first()
    if not session or (session.metadata_json or {}).get("client") != "museum_android":
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.metadata_json.get("audience") != audience:
        raise HTTPException(status_code=409, detail="会话模式不匹配，请切换或创建对应模式会话")
    return session


@router.post("/auth/register", response_model=AuthResponse)
async def register(request: MobileRegisterRequest, db: Session = Depends(get_db)):
    if len(request.password.strip()) < 8:
        raise HTTPException(status_code=400, detail="密码至少需要8位非首尾空格字符")
    return await auth.register(RegisterRequest(
        username=request.username, password=request.password, role="user"
    ), db)


@router.post("/sessions", response_model=SessionInfo)
async def create_session(request: MobileSessionRequest,
                         current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = ChatSession(user_id=current_user.id, session_id=f"mobile-{uuid4().hex}",
                          metadata_json={"client": "museum_android", "audience": request.audience,
                                         "exhibit_id": request.exhibit_id})
    db.add(session)
    db.commit()
    db.refresh(session)
    cache.delete(storage._sessions_cache_key(current_user.username))
    return SessionInfo(session_id=session.session_id, updated_at=session.updated_at.isoformat(),
                       message_count=0, audience=request.audience, exhibit_id=request.exhibit_id)


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(audience: Audience, current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    owned = db.query(ChatSession).filter(ChatSession.user_id == current_user.id).all()
    ids = {s.session_id for s in owned if (s.metadata_json or {}).get("client") == "museum_android"
           and s.metadata_json.get("audience") == audience}
    result = [SessionInfo(**item) for item in storage.list_session_infos(current_user.username)
              if item["session_id"] in ids]
    result.sort(key=lambda item: item.updated_at, reverse=True)
    return SessionListResponse(sessions=result)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, audience: Audience,
                      current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _owned_session(db, current_user, session_id, audience)
    return await sessions.get_session_messages(session_id, current_user, db)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, audience: Audience,
                         current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _owned_session(db, current_user, session_id, audience)
    return await sessions.delete_session(session_id, current_user)


def _chat_request(request: MobileChatRequest, db: Session, user: User):
    _owned_session(db, user, request.session_id, request.audience)
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")
    return ChatRequest(message=request.message, session_id=request.session_id)


@router.post("/chat", response_model=ChatResponse)
async def mobile_chat(request: MobileChatRequest,
                      current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await chat.chat_endpoint(_chat_request(request, db, current_user), current_user)


@router.post("/chat/stream")
async def mobile_stream(request: MobileChatRequest,
                        current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return await chat.chat_stream_endpoint(_chat_request(request, db, current_user), current_user)
