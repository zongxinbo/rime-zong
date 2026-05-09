from __future__ import annotations

from pathlib import Path
from typing import Iterator


def iter_rime_dict_rows(path: Path) -> Iterator[list[str]]:
    in_body = False
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if line.strip() == "...":
                in_body = True
                continue
            if not in_body:
                continue
            if not line.strip() or line.startswith("#"):
                continue
            yield line.split("\t")


def parse_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

