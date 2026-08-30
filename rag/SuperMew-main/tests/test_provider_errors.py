from backend.infra.provider_errors import classify_provider_error


def test_rate_limit_error_is_redacted_and_retryable():
    error = classify_provider_error(
        RuntimeError("Error code: 429 provider-token-redacted SetLimitExceeded")
    )

    assert error.code == "MODEL_RATE_LIMITED"
    assert error.status_code == 429
    assert error.retryable is True
    assert "provider-token-redacted" not in error.detail
    assert "原始错误" not in error.detail


def test_unsupported_response_format_is_a_non_retryable_request_error():
    error = classify_provider_error(
        RuntimeError("This response_format type is unavailable now")
    )

    assert error.code == "PROVIDER_REQUEST_INVALID"
    assert error.status_code == 502
    assert error.retryable is False
    assert "请求格式" in error.message


def test_timeout_and_unknown_errors_have_safe_fallbacks():
    timeout = classify_provider_error(TimeoutError("private endpoint timed out"))
    unknown = classify_provider_error(RuntimeError("provider failed with token abc"))

    assert (timeout.code, timeout.status_code, timeout.retryable) == (
        "MODEL_TIMEOUT",
        504,
        True,
    )
    assert unknown.code == "INTERNAL_ERROR"
    assert unknown.status_code == 500
    assert "token abc" not in unknown.detail
