from __future__ import annotations

from pathlib import Path

from .models import Entry
from .paths import REPO_ROOT


def parse_cangjie_dict(path: Path) -> list[Entry]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_body = False
    entries: list[Entry] = []

    for lineno, line in enumerate(lines, start=1):
        if line.strip() == "...":
            in_body = True
            continue
        if not in_body:
            continue
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        text, code = parts[0], parts[1]
        if not text or not code:
            continue

        if not code.isascii() or not code.islower():
            raise ValueError(f"{path}:{lineno}: 遇到异常编码 {code!r}")

        entries.append(Entry(text=text, code=code))

    return entries


def normalize_prefixes(prefixes: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for item in prefixes:
        for part in item.split(","):
            part = part.strip()
            if part:
                normalized.append(part)
    return tuple(dict.fromkeys(normalized))


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()
