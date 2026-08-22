from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from backend.schemas.chat import HitlResumeState, normalize_rag_trace

logger = logging.getLogger(__name__)


@dataclass
class ChatRequestContext:
    """保存单次对话请求的 RAG 状态，避免并发请求共享全局变量。"""

    user_id: str
    session_id: str
    output_queue: Optional[asyncio.Queue] = None
    loop: Optional[asyncio.AbstractEventLoop] = None

    _lock: threading.RLock = field(default_factory=threading.RLock)
    _active: bool = True
    _rag_trace: Optional[dict] = None
    _hitl_resume_state: Optional[dict] = None
    _knowledge_tool_slots_used: int = 0
    _started_at: float = field(default_factory=time.monotonic)
    _last_step_at: Optional[float] = None

    @classmethod
    def for_stream(
        cls,
        *,
        user_id: str,
        session_id: str,
        output_queue: asyncio.Queue,
    ) -> "ChatRequestContext":
        return cls(
            user_id=user_id,
            session_id=session_id,
            output_queue=output_queue,
            loop=asyncio.get_running_loop(),
        )

    @classmethod
    def for_sync(cls, *, user_id: str, session_id: str) -> "ChatRequestContext":
        return cls(user_id=user_id, session_id=session_id)

    def emit_rag_step(
        self,
        icon: str,
        label: str,
        detail: str = "",
        *,
        group: Optional[str] = None,
        group_label: Optional[str] = None,
    ) -> None:
        with self._lock:
            if not self._active or self.output_queue is None or self.loop is None:
                return
            now = time.monotonic()
            last_step_at = self._last_step_at or self._started_at
            self._last_step_at = now
            step = {
                "icon": icon,
                "label": label,
                "detail": detail,
                "elapsed_ms": max(int((now - self._started_at) * 1000), 0),
                "stage_elapsed_ms": max(int((now - last_step_at) * 1000), 0),
            }
            if group:
                step["group"] = group
            if group_label:
                step["group_label"] = group_label
            queue = self.output_queue
            loop = self.loop

        try:
            if not loop.is_closed():
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "rag_step", "step": step},
                )
        except Exception:
            logger.exception("Failed to emit RAG step")

    def store_rag_trace(
        self,
        rag_trace: Optional[dict],
        hitl_resume_state: Optional[dict] = None,
    ) -> None:
        normalized_trace = normalize_rag_trace(rag_trace)
        if not normalized_trace:
            return
        normalized_resume_state = None
        if isinstance(hitl_resume_state, dict):
            try:
                normalized_resume_state = HitlResumeState.model_validate(
                    hitl_resume_state
                ).model_dump()
            except ValueError:
                normalized_resume_state = None
        with self._lock:
            if self._active:
                self._rag_trace = {"rag_trace": normalized_trace}
                self._hitl_resume_state = normalized_resume_state

    def take_rag_trace(self) -> Optional[dict]:
        with self._lock:
            context = self._rag_trace
            self._rag_trace = None
            if context is not None and self._hitl_resume_state is not None:
                context["hitl_resume_state"] = self._hitl_resume_state
            self._hitl_resume_state = None
            return context

    def peek_rag_trace(self) -> Optional[dict]:
        with self._lock:
            return self._rag_trace

    def peek_hitl_resume_state(self) -> Optional[dict]:
        with self._lock:
            return self._hitl_resume_state

    def reset_knowledge_tool_budget(self) -> None:
        with self._lock:
            self._knowledge_tool_slots_used = 0

    def acquire_knowledge_tool_slot(self) -> bool:
        with self._lock:
            if self._knowledge_tool_slots_used >= 1:
                return False
            self._knowledge_tool_slots_used += 1
            return True

    def close(self) -> None:
        with self._lock:
            self._active = False
            self.output_queue = None
            self.loop = None
