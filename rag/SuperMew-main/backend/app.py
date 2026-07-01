import logging
import os
import sys
import uuid
from pathlib import Path

def dummy_symlink(src, dst, target_is_directory=False, *, dir_fd=None):
    import shutil
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)

if os.name == "nt":
    os.symlink = dummy_symlink

# 支持 `python backend/app.py` 与 `uvicorn backend.app:app` 两种启动方式
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.env import PROJECT_ROOT, load_env

load_env()

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api import router
from backend.infra.auth import warn_insecure_runtime_secrets
from backend.infra.database import init_db

FRONTEND_DIR = PROJECT_ROOT / "frontend" / "dist"
logger = logging.getLogger("museum.bridge")


def create_app() -> FastAPI:
    app = FastAPI(title="博物馆知识库 API")

    def _is_museum_bridge_path(path: str) -> bool:
        return path.startswith("/api/museum/")

    def _get_bridge_trace_id(request: Request) -> str:
        trace_id = getattr(request.state, "bridge_trace_id", "")
        if trace_id:
            return str(trace_id)
        return str(request.headers.get("X-Bridge-Trace-Id") or "").strip()

    def _museum_error_payload(
        *,
        code: int,
        message: str,
        error_code: str,
        query: str = "",
        trace: dict | None = None,
        details: list[str] | None = None,
    ) -> dict:
        return {
            "code": code,
            "message": message,
            "query": query,
            "contexts": [],
            "trace": trace or {},
            "error_code": error_code,
            "details": details or [],
        }

    @app.on_event("startup")
    async def _startup_init_db():
        warn_insecure_runtime_secrets()
        init_db()

    async def _museum_http_exception_handler(request: Request, exc: HTTPException):
        if not _is_museum_bridge_path(request.url.path or ""):
            return await http_exception_handler(request, exc)

        trace_id = _get_bridge_trace_id(request)
        if isinstance(exc.detail, dict):
            payload = {
                "code": exc.detail.get("code", exc.status_code),
                "message": exc.detail.get("message", "桥接请求失败"),
                "query": exc.detail.get("query", ""),
                "contexts": exc.detail.get("contexts", []),
                "trace": exc.detail.get("trace", {}),
                "error_code": exc.detail.get("error_code", "MUSEUM_BRIDGE_HTTP_ERROR"),
                "details": exc.detail.get("details", []),
            }
        else:
            payload = _museum_error_payload(
                code=exc.status_code,
                message=str(exc.detail or "桥接请求失败"),
                error_code="MUSEUM_BRIDGE_HTTP_ERROR",
            )

        logger.warning(
            "museum bridge http error | trace_id=%s | path=%s | status=%s | error_code=%s | details_count=%s",
            trace_id or "-",
            request.url.path,
            exc.status_code,
            payload.get("error_code") or "MUSEUM_BRIDGE_HTTP_ERROR",
            len(payload.get("details") or []),
        )

        response_headers = dict(exc.headers or {})
        if trace_id:
            response_headers["X-Bridge-Trace-Id"] = trace_id
        return JSONResponse(status_code=exc.status_code, content=payload, headers=response_headers)

    async def _museum_validation_exception_handler(request: Request, exc: RequestValidationError):
        if not _is_museum_bridge_path(request.url.path or ""):
            return await request_validation_exception_handler(request, exc)

        trace_id = _get_bridge_trace_id(request)
        details: list[str] = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error.get("loc", []))
            message = error.get("msg", "参数校验失败")
            details.append(f"{location}: {message}" if location else message)

        payload = _museum_error_payload(
            code=42201,
            message="桥接请求参数校验失败",
            error_code="MUSEUM_QUERY_VALIDATION_FAILED",
            details=details,
        )
        logger.warning(
            "museum bridge validation failed | trace_id=%s | path=%s | details=%s",
            trace_id or "-",
            request.url.path,
            details,
        )
        response_headers = {}
        if trace_id:
            response_headers["X-Bridge-Trace-Id"] = trace_id
        return JSONResponse(status_code=422, content=payload, headers=response_headers)

    app.add_exception_handler(HTTPException, _museum_http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _museum_http_exception_handler)
    app.add_exception_handler(RequestValidationError, _museum_validation_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def _no_cache(request, call_next):
        path = request.url.path or ""
        if _is_museum_bridge_path(path):
            trace_id = str(request.headers.get("X-Bridge-Trace-Id") or "").strip() or uuid.uuid4().hex[:16]
            request.state.bridge_trace_id = trace_id

        response = await call_next(request)
        if _is_museum_bridge_path(path):
            trace_id = getattr(request.state, "bridge_trace_id", "")
            if trace_id:
                response.headers["X-Bridge-Trace-Id"] = str(trace_id)
        if path == "/" or path.endswith((".html", ".js", ".css")):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    app.include_router(router)

    if FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))
