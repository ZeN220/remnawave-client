import json

from remnawave.serialization import AdaptixSerializer
from tests.samples import Sample


def test_custom_loads(payload: bytes) -> None:
    seen: list[bytes] = []

    def loads(raw: bytes) -> object:
        seen.append(raw)
        return json.loads(raw)

    AdaptixSerializer(loads=loads).load(payload, Sample)

    assert seen == [payload]


def test_custom_dumps(sample: Sample) -> None:
    def dumps(_data: object) -> bytes:
        return b"stub"

    assert AdaptixSerializer(dumps=dumps).dump(sample) == b"stub"


def test_default_dumps_is_compact(
    serializer: AdaptixSerializer,
    sample: Sample,
) -> None:
    assert b", " not in serializer.dump(sample)
