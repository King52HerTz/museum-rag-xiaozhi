from scripts.evaluate_official_web import (
    compare_modes,
    evaluate_evidence,
    filter_cooccurring_documents,
    run_cases,
    summarize_mode,
)


def test_cooccurrence_filter_requires_each_entity_group_in_same_document():
    documents = [
        {"text": "辛追与利稀的关系资料"},
        {"text": "辛追墓出土资料"},
    ]

    filtered = filter_cooccurring_documents(
        documents,
        [["辛追"], ["利豨", "利稀"]],
    )

    assert filtered == [documents[0]]


def test_evidence_coverage_supports_alias_groups():
    case = {
        "required_term_groups": [["辛追"], ["利豨", "利稀"], ["儿子", "母子"]],
        "cooccurrence_term_groups": [["辛追"], ["利豨", "利稀"]],
    }

    result = evaluate_evidence(case, [{"text": "辛追与儿子利稀的相关资料"}])

    assert result["coverage_rate"] == 1.0
    assert result["full_coverage"] is True


def test_run_cases_falls_back_to_snippet_when_extract_fails():
    case = {
        "id": "case-1",
        "query": "辛追与利豨",
        "required_term_groups": [["辛追"], ["利豨"]],
    }
    source = {
        "filename": "官网：人物资料",
        "text": "辛追与利豨",
        "source_url": "https://www.hnmuseum.com/a",
    }

    def failed_extract(_document, _query):
        error = RuntimeError("failed")
        error.code = "WEB_EXTRACT_UNAVAILABLE"
        raise error

    search_rows, extract_rows = run_cases(
        [case],
        search=lambda _query: [source],
        extract=failed_extract,
        canonical_url=lambda url: url,
        extract_sources=1,
        delay_seconds=0,
    )

    assert search_rows[0]["full_coverage"] is True
    assert extract_rows[0]["full_coverage"] is True
    assert extract_rows[0]["error_code"] == "WEB_EXTRACT_UNAVAILABLE"


def test_decision_requires_quality_gain_and_all_safety_checks():
    search_rows = [
        {
            "full_coverage": False,
            "coverage_rate": 0.5,
            "accepted_document_count": 1,
            "document_count": 1,
            "irrelevant_document_count": 0,
            "error_code": "",
            "latency_ms": 100,
            "whitelist_violation_count": 0,
        }
    ]
    extract_rows = [
        {
            "full_coverage": True,
            "coverage_rate": 1.0,
            "accepted_document_count": 1,
            "document_count": 1,
            "irrelevant_document_count": 0,
            "error_code": "",
            "latency_ms": 500,
            "whitelist_violation_count": 0,
        }
    ]
    decision = compare_modes(
        summarize_mode(search_rows),
        summarize_mode(extract_rows),
        minimum_full_coverage_gain=0.05,
        maximum_extract_p95_ms=1000,
        maximum_provider_error_rate=0.2,
    )

    assert decision["recommend_enable_extract"] is True
    assert all(decision["checks"].values())
