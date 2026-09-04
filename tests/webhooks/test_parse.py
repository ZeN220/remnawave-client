import pytest

from remnawave._generated.models import NodeEvent, UserEvent
from remnawave.exceptions import SerializationError
from remnawave.webhooks import WebhookReceiver


def test_user_event(receiver: WebhookReceiver, user_event: bytes) -> None:
    event = receiver.parse(user_event)

    assert isinstance(event, UserEvent)
    assert event.scope == "user"
    assert event.data.username == "value"


def test_node_event(receiver: WebhookReceiver, node_event: bytes) -> None:
    event = receiver.parse(node_event)

    assert isinstance(event, NodeEvent)
    assert event.scope == "node"


def test_unknown_scope(receiver: WebhookReceiver) -> None:
    with pytest.raises(SerializationError, match="unknown webhook scope"):
        receiver.parse(b'{"scope":"nope"}')


def test_broken_json(receiver: WebhookReceiver) -> None:
    with pytest.raises(SerializationError):
        receiver.parse(b"{not json")


def test_receive_verifies_then_parses(
    receiver: WebhookReceiver,
    user_event: bytes,
) -> None:
    event = receiver.receive(user_event, receiver.sign(user_event))

    assert isinstance(event, UserEvent)
