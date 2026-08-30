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
