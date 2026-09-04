import pytest

from remnawave.execution import BearerAuth


def test_header() -> None:
    assert BearerAuth("secret").headers() == {"Authorization": "Bearer secret"}


def test_empty_token() -> None:
    with pytest.raises(ValueError, match="token"):
        BearerAuth("")


def test_repr_hides_token() -> None:
    assert "secret" not in repr(BearerAuth("secret"))
