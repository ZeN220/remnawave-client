import pytest

from remnawave.webhooks import WebhookReceiver
from tests.generated.examples import example_for, schemas

SECRET = "s3cret"  # noqa: S105


@pytest.fixture
def receiver() -> WebhookReceiver:
    return WebhookReceiver(SECRET)


@pytest.fixture
def secret() -> str:
    return SECRET


@pytest.fixture
def user_event() -> bytes:
    return example_for(schemas()["RemnawaveWebhookUserEventsDto"])


@pytest.fixture
def node_event() -> bytes:
    return example_for(schemas()["RemnawaveWebhookNodeEventsDto"])
