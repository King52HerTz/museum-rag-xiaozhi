import unittest
from unittest.mock import patch

from backend.rag import pipeline
from backend.rag import utils


class _FakeStructuredModel:
    def __init__(self, value):
        self.value = value

    def with_structured_output(self, _schema):
        return self

    def invoke(self, _messages):
        return self.value


class RagCoreCompatibilityTests(unittest.TestCase):
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
            def with_structured_output(self, _schema):
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
        self.assertEqual("answer", result["route"])
        self.assertEqual(docs, result["docs"])

    def test_empty_retrieval_short_circuits_evidence_grader(self):
        with (
            patch.object(pipeline, "retrieve_documents", return_value={"docs": [], "meta": {}}),
            patch.object(pipeline, "_get_grader_model", side_effect=AssertionError("grader should not run")),
        ):
            result = pipeline.run_rag_graph("资料中没有的问题")

        self.assertEqual("no_knowledge", result["retrieval_status"])
        self.assertEqual("no_knowledge", result["route"])
        self.assertEqual([], result["docs"])

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
