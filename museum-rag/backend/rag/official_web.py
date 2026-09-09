"""Bounded official-domain web fallback for museum RAG evidence gaps."""

from __future__ import annotations

import os
import re
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

import requests

from backend.rag.outcomes import outcome_for_status


TAVILY_KEYLESS_ENDPOINT = "https://api.tavily.com/search"
OFFICIAL_WEB_DOMAINS = (
    "hnmuseum.com",
    "chnmuseum.cn",
    "ncha.gov.cn",
    "gov.cn",
    "kaogu.cn",
    "cssn.cn",
)
OFFICIAL_WEB_ENABLED = os.getenv("OFFICIAL_WEB_SUPPLEMENT_ENABLED", "true").lower() != "false"


def _read_positive_int(name: str, default: int, maximum: int) -> int:
    try:
        return min(max(int(os.getenv(name, str(default))), 1), maximum)
    except ValueError:
        return default


def _read_positive_float(name: str, default: float, maximum: float) -> float:
    try:
        return min(max(float(os.getenv(name, str(default))), 0.1), maximum)
    except ValueError:
        return default


OFFICIAL_WEB_MAX_RESULTS = _read_positive_int("OFFICIAL_WEB_MAX_RESULTS", 3, 5)
OFFICIAL_WEB_TIMEOUT_SECONDS = _read_positive_float("OFFICIAL_WEB_TIMEOUT_SECONDS", 8.0, 15.0)
OFFICIAL_WEB_MAX_RESPONSE_BYTES = _read_positive_int(
    "OFFICIAL_WEB_MAX_RESPONSE_BYTES", 262_144, 1_048_576
)
OFFICIAL_WEB_MAX_SNIPPET_CHARACTERS = _read_positive_int(
    "OFFICIAL_WEB_MAX_SNIPPET_CHARACTERS", 1_200, 3_000
)

_MUSEUM_SCOPE_MARKERS = (
    "博物",
    "展览",
    "展品",
    "文物",
    "考古",
    "墓",
    "马王堆",
    "辛追",
    "利苍",
    "利豨",
    "利稀",
)
_SENSITIVE_QUERY_PATTERNS = (
    re.compile(r"https?://", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|password|passwd|secret|token)\b", re.IGNORECASE),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"\b[A-Za-z0-9_-]{32,}\b"),
)


class OfficialWebError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _compact_text(value: Any, maximum: int) -> str:
    text = re.sub(r"<[^>]*>", " ", str(value or ""))
    text = " ".join(text.split())
    return text[:maximum]


def _is_public_museum_query(query: str) -> bool:
    compact = " ".join(str(query or "").split())
    if not compact or len(compact.encode("utf-8")) > 1_200:
        return False
    if not any(marker in compact for marker in _MUSEUM_SCOPE_MARKERS):
        return False
    return not any(pattern.search(compact) for pattern in _SENSITIVE_QUERY_PATTERNS)


def _canonical_official_url(value: str) -> Optional[str]:
    try:
        parsed = urlsplit(str(value or "").strip())
        host = (parsed.hostname or "").casefold().rstrip(".")
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.casefold() != "https"
        or not host
        or parsed.username
        or parsed.password
        or port not in (None, 443)
    ):
        return None
    if not any(host == domain or host.endswith(f".{domain}") for domain in OFFICIAL_WEB_DOMAINS):
        return None
    return urlunsplit(("https", host, parsed.path or "/", parsed.query, ""))


def search_official_web(query: str, *, session: Optional[requests.Session] = None) -> list[dict]:
    if not _is_public_museum_query(query):
        raise OfficialWebError("WEB_QUERY_NOT_PUBLIC_MUSEUM_SCOPE")

    owned_session = session is None
    http = session or requests.Session()
    if owned_session:
        http.trust_env = False
    try:
        response = http.post(
            TAVILY_KEYLESS_ENDPOINT,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Tavily-Access-Mode": "keyless",
                "User-Agent": "museum-rag-official-web/1.0",
            },
            json={
                "query": f"{_compact_text(query, 400)} 湖南博物院 官方",
                "search_depth": "basic",
                "max_results": OFFICIAL_WEB_MAX_RESULTS,
                "include_domains": list(OFFICIAL_WEB_DOMAINS),
            },
            timeout=OFFICIAL_WEB_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        if response.status_code != 200:
            raise OfficialWebError("WEB_SEARCH_PROVIDER_FAILED")
        if len(response.content) > OFFICIAL_WEB_MAX_RESPONSE_BYTES:
            raise OfficialWebError("WEB_SEARCH_RESPONSE_TOO_LARGE")
        try:
            payload = response.json()
        except (ValueError, TypeError):
            raise OfficialWebError("WEB_SEARCH_INVALID_RESPONSE") from None
    except requests.RequestException:
        raise OfficialWebError("WEB_SEARCH_UNAVAILABLE") from None
    finally:
        if owned_session:
            http.close()

    raw_results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(raw_results, list):
        raise OfficialWebError("WEB_SEARCH_INVALID_RESPONSE")

    evidence: list[dict] = []
    seen_urls: set[str] = set()
    for raw in raw_results:
        if not isinstance(raw, dict):
            continue
        url = _canonical_official_url(str(raw.get("url") or ""))
        if not url or url in seen_urls:
            continue
        title = _compact_text(raw.get("title"), 180) or urlsplit(url).hostname or "官方网页"
        snippet = _compact_text(raw.get("content"), OFFICIAL_WEB_MAX_SNIPPET_CHARACTERS)
        if not snippet:
            continue
        seen_urls.add(url)
        evidence.append(
            {
                "filename": f"官网：{title}",
                "page_number": None,
                "text": snippet,
                "source_kind": "official_web",
                "source_url": url,
            }
        )
        if len(evidence) >= OFFICIAL_WEB_MAX_RESULTS:
            break
    return evidence


def supplement_rag_result(query: str, rag_result: dict) -> dict:
    """Add bounded official snippets only when healthy local retrieval is incomplete."""
    result = dict(rag_result or {})
    trace = dict(result.get("rag_trace") or {})
    result["rag_trace"] = trace
    trace["official_web_enabled"] = OFFICIAL_WEB_ENABLED
    if not OFFICIAL_WEB_ENABLED:
        return result

    status = result.get("retrieval_status") or trace.get("retrieval_status")
    degraded = result.get("retrieval_degraded_code") or trace.get("retrieval_degraded_code")
    if status not in ("partial", "no_knowledge") or degraded:
        return result

    trace["official_web_attempted"] = True
    relation_candidates = [
        _compact_text(item, 24)
        for item in (trace.get("relation_candidates") or [])
        if _compact_text(item, 24)
    ][:3]
    web_query = " ".join([query, *relation_candidates]).strip()
    try:
        web_docs = search_official_web(web_query)
    except OfficialWebError as exc:
        trace.update({
            "official_web_status": "failed",
            "official_web_error_code": exc.code,
            "official_web_evidence_count": 0,
        })
        return result

    if relation_candidates:
        web_docs = [
            doc
            for doc in web_docs
            if all(
                candidate in f"{doc.get('filename') or ''} {doc.get('text') or ''}"
                for candidate in relation_candidates
            )
        ]

    if not web_docs:
        trace.update({"official_web_status": "empty", "official_web_evidence_count": 0})
        return result

    local_docs = list(result.get("docs") or [])
    combined = [*local_docs, *web_docs]
    trace.update({
        "official_web_status": "success",
        "official_web_evidence_count": len(web_docs),
        "web_retrieved_chunks": web_docs,
        "retrieved_chunks": combined,
    })
    result.update({
        "docs": combined,
        "retrieval_status": "partial",
        "retrieval_outcome": outcome_for_status("partial").value,
        "route": "answer",
        "rag_trace": trace,
    })
    trace.update({
        "retrieval_status": "partial",
        "retrieval_outcome": outcome_for_status("partial").value,
        "route": "answer",
    })
    return result


__all__ = [
    "OFFICIAL_WEB_DOMAINS",
    "OfficialWebError",
    "search_official_web",
    "supplement_rag_result",
]
