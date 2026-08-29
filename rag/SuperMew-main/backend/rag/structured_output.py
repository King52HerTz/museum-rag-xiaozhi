"""Provider-specific structured-output compatibility helpers."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


def structured_output_method(base_url: str | None) -> str | None:
    """Select a structured-output strategy supported by the configured provider."""

    host = (urlsplit(str(base_url or "")).hostname or "").lower()
    if host == "api.deepseek.com" or host.endswith(".deepseek.com"):
        # DeepSeek's Chat Completions endpoint supports tool/function calling,
        # while its JSON Schema response_format is not accepted by all models.
        return "function_calling"
    return None


def with_structured_output(
    model: Any,
    schema: Any,
    *,
    base_url: str | None = None,
):
    """Bind a Pydantic schema using a provider-compatible LangChain method."""

    method = structured_output_method(base_url)
    if method is None:
        return model.with_structured_output(schema)
    return model.with_structured_output(schema, method=method)


__all__ = ["structured_output_method", "with_structured_output"]
