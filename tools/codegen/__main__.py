import json
import re
import sys
from pathlib import Path

from .overlay import Overlay
from .parse import Builder
from .render import Renderer, polish
from .specs import newest, pinned

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "remnawave"
TARGET = PACKAGE / "_generated"


def _declared_version() -> str:
    text = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'API_VERSION = "([^"]+)"', text)
    return match.group(1) if match else ""


def main() -> int:
    # Версия берётся из пакета: версия библиотеки равна версии API.
    # Аргументом можно перекрыть, чтобы перевести проект на новую спеку.
    wanted = sys.argv[1] if len(sys.argv) > 1 else _declared_version()
    try:
        specs = ROOT / "specs"
        source = pinned(specs, wanted) if wanted else newest(specs)
    except FileNotFoundError as error:
        sys.stdout.write(f"{error}\n")
        return 1

    spec = json.loads(source.read_text(encoding="utf-8"))
    builder = Builder(spec, Overlay.load(ROOT / "overlay.yaml"))
    api = builder.build()

    if TARGET.exists():
        for stale in sorted(TARGET.rglob("*.py"), reverse=True):
            stale.unlink()

    Renderer(api, TARGET, PACKAGE).render()
    polish(TARGET)
    polish(PACKAGE / "types")

    methods = sum(len(g.methods) for g in api.groups)
    sys.stdout.write(
        f"{source.name}: версия {api.version}, "
        f"{len(api.groups)} групп, {methods} методов, "
        f"{len(api.models)} моделей, {len(api.enums)} енумов\n",
    )
    if builder.unsupported:
        count = len(builder.unsupported)
        sys.stdout.write(f"{count} мест без точного типа -> Any\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
