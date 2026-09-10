"""Compare official-web search snippets with bounded Tavily Extract evidence."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Callable
from pathlib import Path
from time import monotonic, sleep

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _normalized_text(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def term_group_matches(text: str, alternatives: list[str]) -> bool:
    normalized = _normalized_text(text)
    return any(_normalized_text(term) in normalized for term in alternatives if term)


def filter_cooccurring_documents(
    documents: list[dict],
    term_groups: list[list[str]],
) -> list[dict]:
    if not term_groups:
        return list(documents)
    return [
        document
        for document in documents
        if all(
            term_group_matches(
                f"{document.get('filename') or ''} {document.get('text') or ''}",
                group,
            )
            for group in term_groups
        )
    ]


def evaluate_evidence(case: dict, documents: list[dict]) -> dict:
    required_groups = case.get("required_term_groups") or []
    accepted = filter_cooccurring_documents(
        documents,
        case.get("cooccurrence_term_groups") or [],
    )
    combined = " ".join(
        f"{document.get('filename') or ''} {document.get('text') or ''}"
        for document in accepted
    )
    covered_groups = sum(
        term_group_matches(combined, group) for group in required_groups
    )
    irrelevant_count = sum(
        not any(
            term_group_matches(
                f"{document.get('filename') or ''} {document.get('text') or ''}",
                group,
            )
            for group in required_groups
        )
        for document in accepted
    )
    return {
        "document_count": len(documents),
        "accepted_document_count": len(accepted),
        "covered_group_count": covered_groups,
        "required_group_count": len(required_groups),
        "coverage_rate": (
            covered_groups / len(required_groups) if required_groups else 1.0
        ),
        "full_coverage": covered_groups == len(required_groups),
        "irrelevant_document_count": irrelevant_count,
    }


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(min(round((len(ordered) - 1) * percentile_value), len(ordered) - 1), 0)
    return ordered[rank]


def summarize_mode(rows: list[dict]) -> dict:
    total = len(rows)
    document_count = sum(row["document_count"] for row in rows)
    return {
        "case_count": total,
        "full_coverage_rate": (
            sum(bool(row["full_coverage"]) for row in rows) / total if total else 0.0
        ),
        "average_coverage_rate": (
            statistics.fmean(row["coverage_rate"] for row in rows) if rows else 0.0
        ),
        "empty_case_rate": (
            sum(row["accepted_document_count"] == 0 for row in rows) / total
            if total
            else 0.0
        ),
        "irrelevant_source_rate": (
            sum(row["irrelevant_document_count"] for row in rows) / document_count
            if document_count
            else 0.0
        ),
        "provider_error_rate": (
            sum(bool(row.get("error_code")) for row in rows) / total if total else 0.0
        ),
        "latency_p50_ms": round(percentile([row["latency_ms"] for row in rows], 0.5)),
        "latency_p95_ms": round(percentile([row["latency_ms"] for row in rows], 0.95)),
        "whitelist_violation_count": sum(
            row.get("whitelist_violation_count", 0) for row in rows
        ),
    }


def compare_modes(
    search_summary: dict,
    extract_summary: dict,
    *,
    minimum_full_coverage_gain: float,
    maximum_extract_p95_ms: int,
    maximum_provider_error_rate: float,
) -> dict:
    coverage_gain = (
        extract_summary["full_coverage_rate"] - search_summary["full_coverage_rate"]
    )
    checks = {
        "coverage_gain": coverage_gain >= minimum_full_coverage_gain,
        "irrelevant_sources_not_increased": (
            extract_summary["irrelevant_source_rate"]
            <= search_summary["irrelevant_source_rate"]
        ),
        "extract_latency": extract_summary["latency_p95_ms"] <= maximum_extract_p95_ms,
        "provider_reliability": (
            extract_summary["provider_error_rate"] <= maximum_provider_error_rate
        ),
        "whitelist_integrity": extract_summary["whitelist_violation_count"] == 0,
    }
    return {
        "recommend_enable_extract": all(checks.values()),
        "full_coverage_gain": round(coverage_gain, 4),
        "checks": checks,
    }


def run_cases(
    cases: list[dict],
    *,
    search: Callable[[str], list[dict]],
    extract: Callable[[dict, str], dict],
    canonical_url: Callable[[str], str | None],
    extract_sources: int,
    delay_seconds: float,
) -> tuple[list[dict], list[dict]]:
    search_rows: list[dict] = []
    extract_rows: list[dict] = []
    for case in cases:
        query = str(case.get("query") or "").strip()
        started = monotonic()
        search_error = ""
        try:
            search_documents = search(query)
        except RuntimeError as exc:
            search_documents = []
            search_error = str(getattr(exc, "code", type(exc).__name__))
        search_latency = (monotonic() - started) * 1000

        search_result = evaluate_evidence(case, search_documents)
        search_result.update({
            "id": case.get("id"),
            "query": query,
            "latency_ms": round(search_latency),
            "error_code": search_error,
            "whitelist_violation_count": sum(
                canonical_url(str(document.get("source_url") or "")) is None
                for document in search_documents
            ),
        })
        search_rows.append(search_result)

        extracted_documents = list(search_documents)
        extract_errors: list[str] = []
        extract_started = monotonic()
        for index, document in enumerate(search_documents[:extract_sources]):
            try:
                extracted_documents[index] = extract(document, query)
            except RuntimeError as exc:
                extract_errors.append(str(getattr(exc, "code", type(exc).__name__)))
        extract_latency = search_latency + (monotonic() - extract_started) * 1000
        extract_result = evaluate_evidence(case, extracted_documents)
        extract_result.update({
            "id": case.get("id"),
            "query": query,
            "latency_ms": round(extract_latency),
            "error_code": extract_errors[0] if extract_errors else search_error,
            "extract_error_codes": extract_errors,
            "whitelist_violation_count": sum(
                canonical_url(str(document.get("source_url") or "")) is None
                for document in extracted_documents
            ),
        })
        extract_rows.append(extract_result)
        if delay_seconds > 0:
            sleep(delay_seconds)
    return search_rows, extract_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="比较官网 Search 摘要与 Tavily Extract 证据质量")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--extract-sources", type=int, default=2, choices=(1, 2, 3))
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    parser.add_argument("--minimum-full-coverage-gain", type=float, default=0.05)
    parser.add_argument("--maximum-extract-p95-ms", type=int, default=15000)
    parser.add_argument("--maximum-provider-error-rate", type=float, default=0.2)
    args = parser.parse_args()

    from backend.env import load_env

    load_env()
    from backend.rag.official_web import (
        _canonical_official_url,
        extract_official_web,
        search_official_web,
    )

    payload = json.loads(args.dataset.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    if args.max_cases > 0:
        cases = cases[: args.max_cases]
    search_rows, extract_rows = run_cases(
        cases,
        search=search_official_web,
        extract=extract_official_web,
        canonical_url=_canonical_official_url,
        extract_sources=args.extract_sources,
        delay_seconds=max(args.delay_seconds, 0),
    )
    search_summary = summarize_mode(search_rows)
    extract_summary = summarize_mode(extract_rows)
    report = {
        "dataset": payload.get("name") or args.dataset.name,
        "search_only": search_summary,
        "search_plus_extract": extract_summary,
        "decision": compare_modes(
            search_summary,
            extract_summary,
            minimum_full_coverage_gain=args.minimum_full_coverage_gain,
            maximum_extract_p95_ms=args.maximum_extract_p95_ms,
            maximum_provider_error_rate=args.maximum_provider_error_rate,
        ),
        "cases": {
            "search_only": search_rows,
            "search_plus_extract": extract_rows,
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
