import pytest

from remnawave.exceptions import NetworkError
from remnawave.execution import ExponentialBackoff
from remnawave.http import Request, Response

GET = Request(method="GET", url="https://panel.example.com/api/users")
POST = Request(method="POST", url="https://panel.example.com/api/users")


def policy(**kwargs: object) -> ExponentialBackoff:
    defaults: dict[str, object] = {"attempts": 3, "base": 1.0, "jitter": False}
    return ExponentialBackoff(**{**defaults, **kwargs})  # type: ignore[arg-type]


def test_retryable_status() -> None:
    assert policy().delay(1, GET, Response(status=503), None) == 1.0


def test_backoff_grows() -> None:
    assert policy().delay(2, GET, Response(status=503), None) == 2.0


def test_max_delay() -> None:
    delay = policy(max_delay=1.5).delay(2, GET, Response(status=503), None)

    assert delay == 1.5


def test_attempts_exhausted() -> None:
    assert policy(attempts=2).delay(2, GET, Response(status=503), None) is None


def test_plain_error_status_is_not_retried() -> None:
    assert policy().delay(1, GET, Response(status=404), None) is None


def test_success_is_not_retried() -> None:
    assert policy().delay(1, GET, Response(status=200), None) is None


def test_post_is_not_retried() -> None:
    assert policy().delay(1, POST, Response(status=503), None) is None


def test_transport_error_is_retried() -> None:
    assert policy().delay(1, GET, None, NetworkError("boom")) == 1.0


def test_retry_after_wins() -> None:
    response = Response(status=429, headers={"Retry-After": "7"})

    assert policy().delay(1, GET, response, None) == 7.0


def test_retry_after_http_date_falls_back() -> None:
    headers = {"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
    response = Response(status=429, headers=headers)

    assert policy().delay(1, GET, response, None) == 1.0


def test_jitter_stays_within_bounds() -> None:
    delays = [
        ExponentialBackoff(attempts=3, base=1.0).delay(
            1,
            GET,
            Response(status=503),
            None,
        )
        for _ in range(50)
    ]

    assert all(d is not None and 0.5 <= d <= 1.0 for d in delays)


def test_attempts_must_be_positive() -> None:
    with pytest.raises(ValueError, match="attempts"):
        ExponentialBackoff(attempts=0)
