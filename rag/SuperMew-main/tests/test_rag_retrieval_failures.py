from types import SimpleNamespace
from unittest.mock import patch

from backend.rag import utils


def test_embedding_failure_exposes_safe_degraded_code():
    with patch.object(
        utils._embedding_service,
        "get_embeddings",
        side_effect=RuntimeError("embedding unavailable"),
    ):
        result = utils.retrieve_documents("测试问题")

    assert result["docs"] == []
    assert result["meta"]["retrieval_mode"] == "failed"
    assert result["meta"]["retrieval_degraded_code"] == "EMBEDDING_UNAVAILABLE"
    assert result["meta"]["provider_error_code"] == "EMBEDDING_UNAVAILABLE"
    assert result["meta"]["provider_error_stage"] == "embedding"


def test_vector_store_failure_exposes_safe_degraded_code_after_fallback():
    with (
        patch.object(utils._embedding_service, "get_embeddings", return_value=[[0.1]]),
        patch.object(
            utils._milvus_manager,
            "hybrid_retrieve",
            side_effect=RuntimeError("hybrid unavailable"),
        ),
        patch.object(
            utils._milvus_manager,
            "dense_retrieve",
            side_effect=RuntimeError("dense unavailable"),
        ),
    ):
        result = utils.retrieve_documents("测试问题")

    assert result["docs"] == []
    assert result["meta"]["retrieval_mode"] == "failed"
    assert result["meta"]["retrieval_degraded_code"] == "VECTOR_STORE_UNAVAILABLE"
    assert result["meta"]["provider_error_code"] == "VECTOR_STORE_UNAVAILABLE"
    assert result["meta"]["provider_error_stage"] == "retrieval"


def test_rerank_http_failure_does_not_expose_provider_response():
    response = SimpleNamespace(
        status_code=429,
        text="provider-token-redacted",
    )
    docs = [{"filename": "guide.md", "text": "湖南博物院位于长沙。", "score": 0.8}]

    with (
        patch.object(utils, "RERANK_ENABLED", True),
        patch.object(utils, "RERANK_MODEL", "rerank-test"),
        patch.object(utils, "RERANK_API_KEY", "provider-token-redacted"),
        patch.object(utils, "RERANK_BINDING_HOST", "http://reranker.test"),
        patch.object(utils.requests, "post", return_value=response),
    ):
        reranked, meta = utils._rerank_documents("博物院在哪里？", docs, top_k=1)

    assert reranked[0]["filename"] == "guide.md"
    assert meta["rerank_error"] == "MODEL_RATE_LIMITED"
    assert meta["rerank_error_code"] == "MODEL_RATE_LIMITED"
    assert meta["rerank_retryable"] is True
    assert "provider-token-redacted" not in str(meta)


def test_rerank_empty_response_has_stable_error_code():
    response = SimpleNamespace(status_code=200, json=lambda: {"results": []})
    docs = [{"filename": "guide.md", "text": "湖南博物院位于长沙。", "score": 0.8}]

    with (
        patch.object(utils, "RERANK_ENABLED", True),
        patch.object(utils, "RERANK_MODEL", "rerank-test"),
        patch.object(utils, "RERANK_API_KEY", "provider-token-redacted"),
        patch.object(utils, "RERANK_BINDING_HOST", "http://reranker.test"),
        patch.object(utils.requests, "post", return_value=response),
    ):
        _reranked, meta = utils._rerank_documents("博物院在哪里？", docs, top_k=1)

    assert meta["rerank_error"] == "RERANK_EMPTY_RESPONSE"
    assert meta["rerank_error_code"] == "RERANK_EMPTY_RESPONSE"
    assert meta["rerank_retryable"] is False
