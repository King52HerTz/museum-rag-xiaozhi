"""Evaluate document-level retrieval against a SuperMew-compatible JSON dataset."""

import argparse
import json
from pathlib import Path
import sys
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def normalize_document_name(value: str) -> str:
    return Path(value or "").stem.strip().lower()


def rank_gold_document(retrieved: list[dict], gold_documents: list[dict]) -> int | None:
    gold_names = {
        normalize_document_name(item.get("canonical_name", ""))
        for item in gold_documents
        if item.get("canonical_name")
    }
    for rank, document in enumerate(retrieved, 1):
        if normalize_document_name(document.get("filename", "")) in gold_names:
            return rank
    return None


def evaluate_cases(
    cases: list[dict],
    retrieve: Callable[[str], dict],
) -> dict:
    evaluated = 0
    hits = 0
    reciprocal_rank_sum = 0.0
    failures = []
    for case in cases:
        gold_documents = case.get("gold_documents") or []
        if not gold_documents:
            continue
        result = retrieve(case["question"])
        documents = result.get("docs") or []
        rank = rank_gold_document(documents, gold_documents)
        evaluated += 1
        if rank is not None:
            hits += 1
            reciprocal_rank_sum += 1 / rank
        else:
            failures.append(
                {
                    "id": case.get("id"),
                    "question": case["question"],
                    "gold": [item.get("canonical_name") for item in gold_documents],
                    "retrieved": [item.get("filename") for item in documents],
                }
            )
    return {
        "evaluated_cases": evaluated,
        "document_recall": hits / evaluated if evaluated else 0.0,
        "mrr": reciprocal_rank_sum / evaluated if evaluated else 0.0,
        "miss_count": len(failures),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="评估当前知识库的文档级 Recall 与 MRR")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--failure-limit", type=int, default=10)
    args = parser.parse_args()

    from backend.env import load_env

    load_env()
    from backend.rag.utils import retrieve_documents

    payload = json.loads(args.dataset.read_text(encoding="utf-8"))
    cases = payload.get("cases") or []
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    report = evaluate_cases(
        cases,
        lambda question: retrieve_documents(question, top_k=max(args.top_k, 1)),
    )
    report["dataset"] = payload.get("name") or args.dataset.name
    report["top_k"] = max(args.top_k, 1)
    report["failures"] = report["failures"][: max(args.failure_limit, 0)]
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
