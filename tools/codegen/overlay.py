from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True, slots=True)
class Overlay:
    groups: dict[str, str] = field(default_factory=dict)
    methods: dict[str, str] = field(default_factory=dict)
    types: dict[str, str] = field(default_factory=dict)
    secret_fields: dict[str, list[str]] = field(default_factory=dict)
    field_types: dict[str, str] = field(default_factory=dict)
    field_names: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Overlay":
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cls(
            groups=raw.get("groups") or {},
            methods=raw.get("methods") or {},
            types=raw.get("types") or {},
            secret_fields=raw.get("secret_fields") or {},
            field_types=raw.get("field_types") or {},
            field_names=raw.get("field_names") or {},
        )
