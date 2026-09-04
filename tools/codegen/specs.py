from pathlib import Path


def pinned(directory: Path, version: str) -> Path:
    """Спека конкретной версии."""
    path = directory / f"openapi-{version}.json"
    if not path.exists():
        message = f"нет {path.name} в {directory}"
        raise FileNotFoundError(message)
    return path


def newest(directory: Path) -> Path:
    """Самая свежая спека в каталоге.

    Сортировать имена как строки нельзя: «3.9.0» лексикографически больше
    «3.10.0». Сравниваем версию покомпонентно.
    """
    found = sorted(directory.glob("openapi-*.json"), key=_version)
    if not found:
        message = f"нет файлов openapi-*.json в {directory}"
        raise FileNotFoundError(message)
    return found[-1]


def _version(path: Path) -> tuple[int, ...]:
    raw = path.stem.removeprefix("openapi-")
    parts = []
    for chunk in raw.split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)
