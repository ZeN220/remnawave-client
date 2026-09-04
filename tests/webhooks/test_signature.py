import pytest

from remnawave.exceptions import WebhookSignatureError
from remnawave.webhooks import WebhookReceiver


def test_sign_is_hmac_sha256(receiver: WebhookReceiver) -> None:
    signed = receiver.sign(b'{"scope":"user"}')

    assert len(signed) == 64
    assert signed == receiver.sign(b'{"scope":"user"}')


def test_verify(receiver: WebhookReceiver) -> None:
    body = b'{"scope":"user"}'

    assert receiver.verify(body, receiver.sign(body)) is True


def test_wrong_signature(receiver: WebhookReceiver) -> None:
    assert receiver.verify(b'{"scope":"user"}', "0" * 64) is False


def test_tampered_body(receiver: WebhookReceiver) -> None:
    signature = receiver.sign(b'{"scope":"user"}')

    assert receiver.verify(b'{"scope":"node"}', signature) is False


def test_other_secret(user_event: bytes) -> None:
    signature = WebhookReceiver("one").sign(user_event)

    assert WebhookReceiver("two").verify(user_event, signature) is False


def test_receive_rejects_bad_signature(
    receiver: WebhookReceiver,
    user_event: bytes,
) -> None:
    with pytest.raises(WebhookSignatureError):
        receiver.receive(user_event, "0" * 64)


def test_empty_secret() -> None:
    with pytest.raises(ValueError, match="secret"):
        WebhookReceiver("")
