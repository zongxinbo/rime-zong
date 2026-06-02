"""按字频语料区域过滤一字多码的仓颉编码。"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .models import Entry
from .paths import SC_GLYPH_PREFERRED_CODE_PATH, TC_GLYPH_PREFERRED_CODE_PATH


def load_glyph_preferred_codes(path: Path) -> dict[str, str]:
    """读取 `字<TAB>编码` 首选表；文件缺失时返回空表。"""
    preferred: dict[str, str] = {}
    if not path.is_file():
        return preferred
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2 or len(parts[0]) != 1 or not parts[1] or any(parts[2:]):
            raise ValueError(f"{path}:{lineno}: 字形首选码格式应为 字<TAB>编码")
        preferred[parts[0]] = parts[1]
    return preferred


def get_glyph_preferred_codes(weights: str) -> dict[str, str]:
    """按权重模式名选择区域首选表。"""
    if "sc" in weights:
        return load_glyph_preferred_codes(SC_GLYPH_PREFERRED_CODE_PATH)
    if "tc" in weights:
        return load_glyph_preferred_codes(TC_GLYPH_PREFERRED_CODE_PATH)
    return {}


def filter_glyph_preferred_entries(
    entries: Iterable[Entry],
    weights: str,
) -> list[Entry]:
    """仅保留区域首选普通码，同时保留 x/z 特种编码。"""
    preferred = get_glyph_preferred_codes(weights)
    return [
        entry
        for entry in entries
        if (
            entry.code.startswith(("x", "z"))
            or entry.text not in preferred
            or entry.code == preferred[entry.text]
        )
    ]
