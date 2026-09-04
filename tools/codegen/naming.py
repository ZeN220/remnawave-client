import keyword
import re

_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_NOT_WORD = re.compile(r"[^0-9a-zA-Z]+")


def snake(name: str) -> str:
    words = _NOT_WORD.sub("_", _BOUNDARY.sub("_", name))
    result = re.sub(r"_+", "_", words).strip("_").lower()
    return f"{result}_" if keyword.iskeyword(result) else result


def pascal(name: str) -> str:
    return "".join(part.title() for part in snake(name).split("_") if part)


_NOT_PLURAL = ("ss", "us", "is", "as")


def singular(name: str) -> str:
    if name.endswith("ies"):
        return f"{name[:-3]}y"
    if name.endswith(("ses", "xes", "zes", "ches", "shes")):
        return name[:-2]
    if name.endswith("s") and not name.endswith(_NOT_PLURAL):
        return name[:-1]
    return name


def enum_member(value: str) -> str:
    member = _NOT_WORD.sub("_", value).strip("_").upper()
    if not member or member[0].isdigit():
        member = f"VALUE_{member}"
    return f"{member}_" if keyword.iskeyword(member.lower()) else member


def camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)
