import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.chat import chat_with_agent, chat_with_agent_stream
from backend.db.models import User
from backend.infra.auth import get_current_user
from backend.infra.provider_errors import classify_provider_error
from backend.schemas import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])
logger = logging.getLogger("chat.api")


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user)):
    try:
        session_id = request.session_id or "default_session"
        resp = chat_with_agent(request.message, current_user.username, session_id)
        if isinstance(resp, dict):
            return ChatResponse(**resp)
        return ChatResponse(response=resp)
    except Exception as e:
        public_error = classify_provider_error(e)
        logger.error(
            "chat request failed | error_type=%s | code=%s",
            type(e).__name__,
            public_error.code,
        )
        raise HTTPException(
            status_code=public_error.status_code,
            detail=public_error.detail,
        ) from e


@router.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest, current_user: User = Depends(get_current_user)):
    async def event_generator():
        try:
            session_id = request.session_id or "default_session"
            async for chunk in chat_with_agent_stream(
                request.message,
                current_user.username,
                session_id,
            ):
                yield chunk
        except Exception as e:
            public_error = classify_provider_error(e)
            logger.error(
                "chat stream failed | error_type=%s | code=%s",
                type(e).__name__,
                public_error.code,
            )
            error_data = {
                "type": "error",
                "code": public_error.code,
                "content": public_error.detail,
                "retryable": public_error.retryable,
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
