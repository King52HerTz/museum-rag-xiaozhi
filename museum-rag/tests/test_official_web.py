from unittest.mock import patch

import pytest

from backend.rag import official_web


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.content = b"{}"

    def json(self):
        return self._payload


class _Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_official_url_rejects_domain_suffix_tricks_and_non_https():
    assert official_web._canonical_official_url("https://www.hnmuseum.com/page")
    assert official_web._canonical_official_url("https://hnmuseum.com.evil.test/page") is None
    assert official_web._canonical_official_url("http://www.hnmuseum.com/page") is None
    assert official_web._canonical_official_url("https://user@www.hnmuseum.com/page") is None


def test_search_uses_fixed_keyless_endpoint_and_filters_results():
    session = _Session(
        _Response({
            "results": [
                {"url": "https://www.hnmuseum.com/a", "title": " 馆方 页面 ", "content": "可靠摘要"},
                {"url": "https://hnmuseum.com.evil.test/b", "title": "伪造", "content": "不可信"},
            ]
        })
    )

    docs = official_web.search_official_web("辛追墓相关文物", session=session)

    assert len(docs) == 1
    assert docs[0]["source_kind"] == "official_web"
    assert docs[0]["source_url"] == "https://www.hnmuseum.com/a"
    assert session.calls[0][0] == official_web.TAVILY_KEYLESS_ENDPOINT
    request = session.calls[0][1]
    assert request["allow_redirects"] is False
    assert request["headers"]["X-Tavily-Access-Mode"] == "keyless"
    assert request["json"]["include_domains"] == list(official_web.OFFICIAL_WEB_DOMAINS)


@pytest.mark.parametrize(
    "query",
    [
        "帮我搜索普通聊天内容",
        "博物馆资料发到 test@example.com",
        "查询文物 token abcdefghijklmnopqrstuvwxyz1234567890",
    ],
)
def test_non_museum_or_sensitive_queries_are_not_sent(query):
    with pytest.raises(official_web.OfficialWebError) as error:
        official_web.search_official_web(query, session=_Session(_Response({"results": []})))
    assert error.value.code == "WEB_QUERY_NOT_PUBLIC_MUSEUM_SCOPE"


def test_partial_result_adds_official_evidence_and_keeps_local_first():
    local = {"filename": "本地资料.docx", "text": "本地片段"}
    web = {
        "filename": "官网：补充资料",
        "text": "小雨的网页摘要",
        "source_kind": "official_web",
        "source_url": "https://www.hnmuseum.com/page",
    }
    with (
        patch.object(official_web, "OFFICIAL_WEB_ENABLED", True),
        patch.object(official_web, "search_official_web", return_value=[web]),
    ):
        result = official_web.supplement_rag_result(
            "辛追夫人的儿子介绍一下",
            {
                "docs": [local],
                "retrieval_status": "partial",
                "retrieval_outcome": "INSUFFICIENT_EVIDENCE",
                "route": "answer",
                "rag_trace": {
                    "retrieval_status": "partial",
                    "relation_candidates": ["小雨"],
                },
            },
        )

    assert result["docs"] == [local, web]
    assert result["retrieval_status"] == "partial"
    assert result["rag_trace"]["official_web_status"] == "success"
    assert result["rag_trace"]["web_retrieved_chunks"] == [web]


def test_relation_candidates_must_all_appear_in_official_snippet():
    matching = {
        "filename": "官网：人物资料",
        "text": "张先生和小雨的家庭关系资料",
        "source_kind": "official_web",
        "source_url": "https://www.hnmuseum.com/match",
    }
    unrelated = {
        "filename": "官网：张先生新闻",
        "text": "没有目标人物",
        "source_kind": "official_web",
        "source_url": "https://www.hnmuseum.com/unrelated",
    }
    with (
        patch.object(official_web, "OFFICIAL_WEB_ENABLED", True),
        patch.object(
            official_web,
            "search_official_web",
            return_value=[unrelated, matching],
        ) as search,
    ):
        result = official_web.supplement_rag_result(
            "介绍张先生的女儿",
            {
                "docs": [],
                "retrieval_status": "no_knowledge",
                "rag_trace": {"relation_candidates": ["张先生", "小雨"]},
            },
        )

    assert search.call_args.args[0].endswith("张先生 小雨")
    assert result["docs"] == [matching]


def test_answerable_result_skips_web_search():
    with (
        patch.object(official_web, "OFFICIAL_WEB_ENABLED", True),
        patch.object(official_web, "search_official_web") as search,
    ):
        result = official_web.supplement_rag_result(
            "马王堆展览有几个单元",
            {"docs": [{"filename": "展览.docx"}], "retrieval_status": "answerable"},
        )

    search.assert_not_called()
    assert result["docs"][0]["filename"] == "展览.docx"


def test_web_failure_preserves_local_partial_result():
    local = {"filename": "本地资料.docx", "text": "本地片段"}
    with (
        patch.object(official_web, "OFFICIAL_WEB_ENABLED", True),
        patch.object(
            official_web,
            "search_official_web",
            side_effect=official_web.OfficialWebError("WEB_SEARCH_UNAVAILABLE"),
        ),
    ):
        result = official_web.supplement_rag_result(
            "辛追墓资料",
            {"docs": [local], "retrieval_status": "partial", "rag_trace": {}},
        )

    assert result["docs"] == [local]
    assert result["retrieval_status"] == "partial"
    assert result["rag_trace"]["official_web_error_code"] == "WEB_SEARCH_UNAVAILABLE"
