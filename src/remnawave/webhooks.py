import hmac
import json
from hashlib import sha256

from remnawave._generated.renames import NAME_MAPPING
from remnawave._generated.webhooks import BY_SCOPE, WebhookEvent
from remnawave.exceptions import SerializationError, WebhookSignatureError
from remnawave.serialization import (
    AdaptixSerializer,
    JsonLoads,
    Serializer,
    build_default_retort,
)

SIGNATURE_HEADER = "x-remnawave-signature"
TIMESTAMP_HEADER = "x-remnawave-timestamp"


class WebhookReceiver:
    def __init__(
        self,
        secret: str,
        serializer: Serializer | None = None,
        loads: JsonLoads | None = None,
    ) -> None:
        if not secret:
            message = "secret must not be empty"
            raise ValueError(message)
        self._secret = secret.encode()
        self._serializer = serializer or AdaptixSerializer(
            build_default_retort(*NAME_MAPPING),
        )
        self._loads = loads or json.loads

    def sign(self, body: bytes) -> str:
        return hmac.new(self._secret, body, sha256).hexdigest()

    def verify(self, body: bytes, signature: str) -> bool:
        return hmac.compare_digest(self.sign(body), signature)

    def parse(self, body: bytes) -> WebhookEvent:
        try:
            payload = self._loads(body)
        except ValueError as exc:
            raise SerializationError(str(exc)) from exc

        scope = payload.get("scope") if isinstance(payload, dict) else None
        event = BY_SCOPE.get(scope) if isinstance(scope, str) else None
        if event is None:
            message = f"unknown webhook scope: {scope!r}"
            raise SerializationError(message)
        return self._serializer.load(body, event)

    def receive(self, body: bytes, signature: str) -> WebhookEvent:
        if not self.verify(body, signature):
            message = "webhook signature does not match"
            raise WebhookSignatureError(message)
        return self.parse(body)
