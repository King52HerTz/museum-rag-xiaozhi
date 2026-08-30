import unittest
from unittest.mock import patch

from backend.rag import pipeline
from backend.rag import utils


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


if __name__ == "__main__":
    unittest.main()
