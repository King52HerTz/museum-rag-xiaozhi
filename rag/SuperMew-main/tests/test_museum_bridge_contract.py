import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError

from backend.api.resources import is_supported_document
from backend.api.routes import museum


class MuseumBridgeContractTests(unittest.TestCase):
    def test_supported_document_formats_match_management_contract(self):
        supported = [
            "collection.pdf",
            "collection.docx",
            "collection.doc",
            "collection.xlsx",
            "collection.xls",
            "collection.html",
            "collection.htm",
        ]
        unsupported = [
            "collection.txt",
            "collection.pptx",
            "collection.zip",
            "collection.pdf.exe",
        ]

        for filename in supported:
            with self.subTest(filename=filename):
                self.assertTrue(is_supported_document(filename))
        for filename in unsupported:
            with self.subTest(filename=filename):
                self.assertFalse(is_supported_document(filename))

    def test_request_defaults_and_top_k_validation(self):
        request = museum.MuseumQueryRequest(question="素纱单衣为什么有名？")

        self.assertEqual("湖南省博物馆", request.museum)
        self.assertEqual("museum_guide", request.scene)
        self.assertEqual(5, request.top_k)
        self.assertTrue(request.need_trace)

        with self.assertRaises(ValidationError):
            museum.MuseumQueryRequest(question="问题", top_k=0)
        with self.assertRaises(ValidationError):
            museum.MuseumQueryRequest(question="问题", top_k=11)

    def test_structured_context_is_added_to_retrieval_query(self):
        request = museum.MuseumQueryRequest(
            question="为什么有名？",
            museum="湖南省博物馆",
            exhibition="长沙马王堆汉墓陈列",
            exhibit_id="M-001",
            era="西汉",
            category="纺织品",
        )

        self.assertEqual(
            "\n".join(
                [
                    "博物馆：湖南省博物馆",
                    "展览：长沙马王堆汉墓陈列",
                    "展品编号：M-001",
                    "时代：西汉",
                    "类别：纺织品",
                    "游客问题：为什么有名？",
                ]
            ),
            museum._build_retrieval_query(request),
        )

    def test_filename_filter_escapes_milvus_string_values(self):
        self.assertEqual(
            'filename in ["normal.pdf", "museum\\\\guide\\\"v1.pdf"]',
            museum._build_filename_filter(["normal.pdf", 'museum\\guide"v1.pdf']),
        )
        self.assertEqual("", museum._build_filename_filter([]))

    def test_query_returns_contexts_and_filter_trace(self):
        request = museum.MuseumQueryRequest(
            question="素纱单衣为什么有名？",
            exhibition="长沙马王堆汉墓陈列",
            top_k=2,
        )
        http_request = SimpleNamespace(
            state=SimpleNamespace(bridge_trace_id="trace-test"),
            headers={},
        )
        calls = []

        def fake_retrieve(query, **kwargs):
            calls.append((query, kwargs))
            return {
                "docs": [
                    {
                        "filename": "马王堆展品.pdf",
                        "text": "素纱单衣是西汉时期的纺织品。",
                        "page_number": 3,
                        "score": 0.91,
                        "chunk_id": "chunk-1",
                    }
                ],
                "meta": {
                    "retrieval_mode": "hybrid",
                    "retrieval_empty": False,
                    "rerank_error": None,
                    "document_filter_applied": True,
                    "document_filter_mode": "structured",
                    "document_filter_count": 1,
                },
            }

        with (
            patch.object(museum.document_profile_store, "find_filenames", return_value=["马王堆展品.pdf"]),
            patch.object(museum, "retrieve_documents", side_effect=fake_retrieve),
        ):
            response = asyncio.run(museum.museum_query(http_request, request))

        self.assertEqual(0, response.code)
        self.assertEqual("检索成功", response.message)
        self.assertEqual(1, len(response.contexts))
        self.assertEqual("马王堆展品.pdf", response.contexts[0].source)
        self.assertEqual("chunk-1", response.contexts[0].chunk_id)
        self.assertEqual("structured", response.trace["document_filter_mode"])
        self.assertEqual(1, len(calls))
        self.assertIn('filename in ["马王堆展品.pdf"]', calls[0][1]["filter_expr"])

    def test_query_falls_back_to_semantic_retrieval_when_filter_is_empty(self):
        request = museum.MuseumQueryRequest(
            question="马王堆汉墓在哪里？",
            museum="湖南省博物馆",
        )
        http_request = SimpleNamespace(state=SimpleNamespace(bridge_trace_id=""), headers={})
        calls = []

        def fake_retrieve(query, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return {"docs": [], "meta": {"retrieval_empty": True}}
            return {
                "docs": [{"filename": "guide.pdf", "text": "长沙。"}],
                "meta": {"retrieval_mode": "dense_fallback", "retrieval_empty": False},
            }

        with (
            patch.object(museum.document_profile_store, "find_filenames", return_value=["guide.pdf"]),
            patch.object(museum, "retrieve_documents", side_effect=fake_retrieve),
        ):
            response = asyncio.run(museum.museum_query(http_request, request))

        self.assertEqual(0, response.code)
        self.assertEqual(1, len(response.contexts))
        self.assertEqual(2, len(calls))
        self.assertIn("filename in [\"guide.pdf\"]", calls[0]["filter_expr"])
        self.assertEqual("", calls[1].get("filter_expr", ""))
        self.assertEqual("semantic_only", calls[1]["trace_context"]["document_filter_fallback"])

    def test_query_returns_successful_empty_response_without_fake_context(self):
        request = museum.MuseumQueryRequest(question="资料中没有的问题", need_trace=False)
        http_request = SimpleNamespace(state=SimpleNamespace(bridge_trace_id=""), headers={})

        with (
            patch.object(museum.document_profile_store, "find_filenames", return_value=[]),
            patch.object(
                museum,
                "retrieve_documents",
                return_value={"docs": [], "meta": {"retrieval_empty": True}},
            ),
        ):
            response = asyncio.run(museum.museum_query(http_request, request))

        self.assertEqual(0, response.code)
        self.assertEqual("未检索到相关资料", response.message)
        self.assertEqual([], response.contexts)
        self.assertEqual({}, response.trace)

    def test_query_failure_redacts_provider_details(self):
        request = museum.MuseumQueryRequest(question="黑地彩绘棺的尺寸？")
        http_request = SimpleNamespace(state=SimpleNamespace(bridge_trace_id="trace-error"), headers={})

        with patch.object(
            museum.document_profile_store,
            "find_filenames",
            side_effect=RuntimeError("provider-token-redacted"),
        ):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(museum.museum_query(http_request, request))

        detail = context.exception.detail
        self.assertEqual("MUSEUM_QUERY_FAILED", detail["error_code"])
        self.assertEqual("[INTERNAL_ERROR] 服务暂时不可用，请稍后重试。", detail["details"][0])
        self.assertNotIn("provider-token-redacted", str(detail))


if __name__ == "__main__":
    unittest.main()
