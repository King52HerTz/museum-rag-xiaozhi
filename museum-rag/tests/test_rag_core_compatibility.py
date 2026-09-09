import unittest
from unittest.mock import patch

from backend.rag import pipeline
from backend.rag import utils
from backend.schemas.chat import normalize_rag_trace


class _FakeStructuredModel:
    def __init__(self, value):
        self.value = value

    def with_structured_output(self, _schema, **_kwargs):
        return self

    def invoke(self, _messages):
        return self.value


class RagCoreCompatibilityTests(unittest.TestCase):
    def test_complex_synthesis_marks_uncovered_sub_questions_as_partial(self):
        class FakeContext:
            def emit_rag_step(self, *_args, **_kwargs):
                return None

        result = pipeline.synthesis(
            {
                "question": "比较两件文物的特点",
                "request_context": FakeContext(),
                "rag_trace": {},
                "sub_results": [
                    {
                        "question": "黑地彩绘棺的特点是什么？",
                        "docs": [{
                            "filename": "black-coffin.md",
                            "text": "官方资料片段",
                        }],
                        "retrieval_status": "answerable",
                        "rag_trace": {
                            "query": "黑地彩绘棺的特点是什么？",
                            "retrieval_status": "answerable",
                        },
                    },
                    {
                        "question": "另一件文物的特点是什么？",
                        "docs": [],
                        "retrieval_status": "no_knowledge",
                        "rag_trace": {
                            "query": "另一件文物的特点是什么？",
                            "retrieval_status": "no_knowledge",
                        },
                    },
                ],
            }
        )

        self.assertEqual("partial", result["retrieval_status"])
        self.assertEqual("INSUFFICIENT_EVIDENCE", result["retrieval_outcome"])
        self.assertEqual("answer", result["route"])
        self.assertEqual(
            ["另一件文物的特点是什么？"],
            result["rag_trace"]["coverage_gap_questions"],
        )

    def test_sync_wrapper_creates_and_closes_legacy_context(self):
        captured = {}

        def fake_invoke(state):
            captured["context"] = state["request_context"]
            return {"route": "answer", "retrieval_status": "answerable"}

        with patch.object(pipeline.rag_graph, "invoke", side_effect=fake_invoke):
            result = pipeline.run_rag_graph("测试问题")

        self.assertEqual("answer", result["route"])
        self.assertFalse(captured["context"]._active)

    def test_upgraded_pipeline_returns_supported_evidence(self):
        class FakeGrader:
            def with_structured_output(self, _schema, **_kwargs):
                return self

            def invoke(self, _messages):
                return pipeline.EvidenceGrade(
                    relevance="strong",
                    answerability="sufficient",
                    ambiguity="none",
                    route="answer",
                    confidence=0.9,
                    reason="mocked evidence",
                )

        docs = [{"filename": "guide.pdf", "page_number": 1, "text": "湖南省博物馆"}]
        with (
            patch.object(pipeline, "retrieve_documents", return_value={"docs": docs, "meta": {}}),
            patch.object(pipeline, "_get_grader_model", return_value=FakeGrader()),
        ):
            result = pipeline.run_rag_graph("湖南省博物馆是什么")

        self.assertEqual("answerable", result["retrieval_status"])
        self.assertEqual("ANSWERABLE", result["retrieval_outcome"])
        self.assertEqual("answer", result["route"])
        self.assertEqual(docs, result["docs"])
        self.assertGreater(result["rag_trace"]["grader_evidence_characters"], 0)
        self.assertEqual(0, result["rag_trace"]["grader_evidence_omitted_count"])

    def test_empty_retrieval_short_circuits_evidence_grader(self):
        with (
            patch.object(pipeline, "retrieve_documents", return_value={"docs": [], "meta": {}}),
            patch.object(pipeline, "_get_grader_model", side_effect=AssertionError("grader should not run")),
        ):
            result = pipeline.run_rag_graph("资料中没有的问题")

        self.assertEqual("no_knowledge", result["retrieval_status"])
        self.assertEqual("NO_KNOWLEDGE", result["retrieval_outcome"])
        self.assertEqual("no_knowledge", result["route"])
        self.assertEqual([], result["docs"])
        self.assertEqual(0, result["rag_trace"]["grader_evidence_characters"])

    def test_retrieval_failure_is_not_reported_as_no_knowledge(self):
        degraded_meta = {
            "retrieval_degraded_code": "EMBEDDING_UNAVAILABLE",
            "provider_error_code": "EMBEDDING_UNAVAILABLE",
            "provider_error_stage": "embedding",
        }
        with (
            patch.object(
                pipeline,
                "retrieve_documents",
                return_value={"docs": [], "meta": degraded_meta},
            ),
            patch.object(
                pipeline,
                "_get_grader_model",
                side_effect=AssertionError("grader should not run"),
            ),
        ):
            result = pipeline.run_rag_graph("临时检索失败的问题")

        self.assertEqual("insufficient_evidence", result["retrieval_status"])
        self.assertEqual("INSUFFICIENT_EVIDENCE", result["retrieval_outcome"])
        self.assertEqual("insufficient_evidence", result["route"])
        self.assertEqual(
            "EMBEDDING_UNAVAILABLE",
            result["rag_trace"]["retrieval_degraded_code"],
        )

    def test_structured_rewrite_plan_keeps_only_selected_method(self):
        rewrite = utils.RewritePlan(
            method="hyde",
            hyde_document="湖南省博物馆展陈资料中的相关段落",
        )
        with patch.object(utils, "_get_rewrite_model", return_value=_FakeStructuredModel(rewrite)):
            result = utils.rewrite_query_once("这个展品有什么意义？")

        self.assertEqual("hyde", result["rewrite_method"])
        self.assertEqual("", result["step_back_question"])
        self.assertIn("假设性答案文档", result["rewritten_query"])

    def test_rerank_error_fields_survive_trace_normalization(self):
        trace = normalize_rag_trace(
            {
                "retrieval_mode": "hybrid",
                "rerank_error": "MODEL_RATE_LIMITED",
                "rerank_error_code": "MODEL_RATE_LIMITED",
                "rerank_retryable": True,
            }
        )

        self.assertEqual("MODEL_RATE_LIMITED", trace["rerank_error"])
        self.assertEqual("MODEL_RATE_LIMITED", trace["rerank_error_code"])
        self.assertTrue(trace["rerank_retryable"])

    def test_local_rerank_promotes_exact_person_and_relationship_evidence(self):
        docs = [
            {"filename": "辛追遗体.docx", "text": "辛追夫人的遗体保存与保护研究。", "score": 0.9},
            {"filename": "妾辛追印.docx", "text": "辛追墓出土了妾辛追印。", "score": 0.8},
            {
                "filename": "03_利苍一家与西汉长沙国背景.docx",
                "text": "辛追夫人与利苍的儿子利豨继承了父亲的爵位。",
                "score": 0.5,
            },
        ]

        reranked = utils._local_lexical_rerank("介绍一下辛追夫人的儿子利豨", docs)

        self.assertEqual("03_利苍一家与西汉长沙国背景.docx", reranked[0]["filename"])
        self.assertGreater(reranked[0]["local_rerank_score"], reranked[1]["local_rerank_score"])

    def test_relationship_target_outweighs_repeated_broad_subject(self):
        docs = [
            {
                "filename": "辛追夫人与遗体保护边界.docx",
                "text": "辛追夫人的遗体保护和数字化研究。",
                "score": 0.9,
            },
            {
                "filename": "03_利苍一家与西汉长沙国背景.docx",
                "text": "利苍一家三口包括辛追和利豨。",
                "score": 0.5,
            },
        ]

        reranked = utils._local_lexical_rerank("介绍一下辛追夫人的儿子利豨", docs)

        self.assertEqual("03_利苍一家与西汉长沙国背景.docx", reranked[0]["filename"])
        self.assertEqual({"利豨"}, utils._query_focus_terms("辛追夫人的儿子利豨"))

    def test_general_question_keeps_rrf_order(self):
        docs = [
            {"filename": "常见问答.docx", "text": "马王堆出土文物概览。", "score": 0.9},
            {"filename": "漆器与髹漆工艺.docx", "text": "马王堆出土七百余件漆器。", "score": 0.8},
        ]

        reranked = utils._local_lexical_rerank("马王堆出土了多少件漆器？", docs)

        self.assertEqual(["常见问答.docx", "漆器与髹漆工艺.docx"], [d["filename"] for d in reranked])
        self.assertEqual(set(), utils._query_focus_terms("辛追夫人的儿子是谁？"))

    def test_document_diversity_prefers_other_sources_before_refill(self):
        docs = [
            {"filename": "A.docx", "text": "A1"},
            {"filename": "A.docx", "text": "A2"},
            {"filename": "A.docx", "text": "A3"},
            {"filename": "B.docx", "text": "B1"},
        ]

        with patch.object(utils, "RETRIEVAL_MAX_CHUNKS_PER_DOCUMENT", 2):
            selected, changed = utils._prefer_document_diversity(docs, top_k=3)

        self.assertEqual(["A1", "A2", "B1"], [item["text"] for item in selected])
        self.assertTrue(changed)

    def test_local_rerank_trace_survives_normalization(self):
        trace = normalize_rag_trace(
            {
                "local_rerank_enabled": True,
                "local_rerank_applied": True,
                "rerank_backend": "local_cross_encoder",
                "retrieval_max_chunks_per_document": 2,
                "document_diversity_applied": True,
            }
        )

        self.assertTrue(trace["local_rerank_applied"])
        self.assertTrue(trace["document_diversity_applied"])
        self.assertEqual(2, trace["retrieval_max_chunks_per_document"])
        self.assertEqual("local_cross_encoder", trace["rerank_backend"])

    def test_local_cross_encoder_reranks_and_records_backend(self):
        class FakeCrossEncoder:
            def predict(self, pairs, **_kwargs):
                self.pairs = pairs
                return [-2.0, 3.0]

        docs = [
            {"filename": "A.docx", "text": "泛化资料", "score": 0.9},
            {"filename": "B.docx", "text": "精确资料", "score": 0.5},
        ]
        with (
            patch.object(utils, "RERANK_MODEL", None),
            patch.object(utils, "RERANK_API_KEY", None),
            patch.object(utils, "RERANK_BINDING_HOST", None),
            patch.object(utils, "LOCAL_CROSS_ENCODER_MODEL", "local-test-model"),
            patch.object(utils, "LOCAL_CROSS_ENCODER_WEIGHT", 0.8),
            patch.object(utils, "_get_local_cross_encoder", return_value=FakeCrossEncoder()),
        ):
            ranked, meta = utils._rerank_documents("精确问题", docs, top_k=2)

        self.assertEqual("B.docx", ranked[0]["filename"])
        self.assertEqual("local_cross_encoder", meta["rerank_backend"])
        self.assertTrue(meta["rerank_applied"])
        self.assertIsNone(meta["rerank_error"])

    def test_cross_encoder_fusion_preserves_strong_rrf_evidence(self):
        class FakeCrossEncoder:
            def predict(self, _pairs, **_kwargs):
                return [0.1, 0.9]

        docs = [
            {"filename": "exact-bm25.docx", "text": "四个单元", "score": 0.9, "rrf_rank": 1},
            {"filename": "semantic.docx", "text": "展览内容", "score": 0.8, "rrf_rank": 2},
        ]
        with (
            patch.object(utils, "LOCAL_CROSS_ENCODER_WEIGHT", 0.2),
            patch.object(utils, "_get_local_cross_encoder", return_value=FakeCrossEncoder()),
        ):
            ranked = utils._rerank_with_local_cross_encoder("哪四个单元", docs)

        self.assertEqual("exact-bm25.docx", ranked[0]["filename"])
        self.assertIn("rerank_fused_score", ranked[0])

    def test_local_cross_encoder_failure_falls_back_without_details(self):
        docs = [{"filename": "A.docx", "text": "资料", "score": 0.9}]
        with (
            patch.object(utils, "RERANK_MODEL", None),
            patch.object(utils, "RERANK_API_KEY", None),
            patch.object(utils, "RERANK_BINDING_HOST", None),
            patch.object(utils, "LOCAL_CROSS_ENCODER_MODEL", "missing-model"),
            patch.object(utils, "_get_local_cross_encoder", side_effect=RuntimeError("private path")),
        ):
            ranked, meta = utils._rerank_documents("问题", docs, top_k=1)

        self.assertEqual("A.docx", ranked[0]["filename"])
        self.assertEqual("LOCAL_RERANK_UNAVAILABLE", meta["rerank_error_code"])
        self.assertNotIn("private path", str(meta))

    def test_missing_external_reranker_uses_local_fallback(self):
        docs = [
            {"filename": "辛追遗体.docx", "text": "辛追遗体保护。", "score": 0.9},
            {"filename": "利苍一家.docx", "text": "辛追的儿子利豨。", "score": 0.5},
        ]

        with (
            patch.object(utils, "RERANK_ENABLED", False),
            patch.object(utils, "LOCAL_CROSS_ENCODER_MODEL", None),
            patch.object(utils, "LOCAL_LEXICAL_RERANK_ENABLED", True),
        ):
            ranked, meta = utils._rerank_documents("辛追的儿子利豨", docs, top_k=2)

        self.assertEqual("利苍一家.docx", ranked[0]["filename"])
        self.assertFalse(meta["rerank_applied"])
        self.assertTrue(meta["local_rerank_applied"])


if __name__ == "__main__":
    unittest.main()
