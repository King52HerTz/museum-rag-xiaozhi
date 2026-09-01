from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PublicProviderError:
    """A redacted, stable error contract for model/provider failures."""

    code: str
    status_code: int
    message: str
    retryable: bool

    @property
    def detail(self) -> str:
        return f"[{self.code}] {self.message}"


def _status_code(error: BaseException) -> int | None:
    for value in (
        getattr(error, "status_code", None),
        getattr(error, "status", None),
    ):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if 400 <= parsed <= 599:
            return parsed
    match = re.search(r"(?:Error code|status code)\s*[:=]\s*(\d{3})", str(error), re.I)
    return int(match.group(1)) if match else None


def classify_provider_error(error: BaseException) -> PublicProviderError:
    """Map common provider failures to safe public messages without raw details."""

    text = str(error or "")
    normalized = text.lower()
    status = _status_code(error)

    if status == 429 or any(
        marker in normalized
        for marker in ("rate limit", "too many requests", "setlimitexceeded")
    ):
        return PublicProviderError(
            code="MODEL_RATE_LIMITED",
            status_code=429,
            message="上游模型服务当前繁忙或已达到额度限制，请稍后重试或检查模型配额。",
            retryable=True,
        )

    if status in (401, 403) or any(
        marker in normalized
        for marker in ("authentication", "unauthorized", "invalid api key")
    ):
        return PublicProviderError(
            code="PROVIDER_AUTHENTICATION_FAILED",
            status_code=503,
            message="模型服务鉴权失败，请检查服务端模型配置。",
            retryable=False,
        )

    if status in (400, 422) or "response_format" in normalized or "invalid_request_error" in normalized:
        return PublicProviderError(
            code="PROVIDER_REQUEST_INVALID",
            status_code=502,
            message="模型服务不支持当前请求格式，请检查模型兼容性配置。",
            retryable=False,
        )

    if isinstance(error, TimeoutError) or any(
        marker in normalized for marker in ("timeout", "timed out", "deadline exceeded")
    ):
        return PublicProviderError(
            code="MODEL_TIMEOUT",
            status_code=504,
            message="模型服务响应超时，请稍后重试。",
            retryable=True,
        )

    if status in (500, 502, 503, 504) or any(
        marker in normalized
        for marker in ("connection", "connecterror", "service unavailable", "temporarily unavailable")
    ):
        return PublicProviderError(
            code="MODEL_UNAVAILABLE",
            status_code=503,
            message="模型服务暂时不可用，请稍后重试。",
            retryable=True,
        )

    return PublicProviderError(
        code="INTERNAL_ERROR",
        status_code=500,
        message="服务暂时不可用，请稍后重试。",
        retryable=False,
    )


__all__ = ["PublicProviderError", "classify_provider_error"]
