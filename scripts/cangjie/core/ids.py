from __future__ import annotations

import sys
from pathlib import Path

from .paths import IDS_PATH


_LR = set("⿰⿲")
_UD = set("⿱⿳")
_WRAP = set("⿴⿵⿶⿷⿸⿹⿺⿻")


def load_ids_structure_map(ids_path: Path = None) -> dict[str, str]:
    """从 ids.txt 加载汉字结构映射：char -> suffix_key (a/s/d/f)。"""
    if ids_path is None:
        ids_path = IDS_PATH
    mapping: dict[str, str] = {}
    if not ids_path.exists():
        print(f"Warning: IDS file not found: {ids_path}", file=sys.stderr)
        return mapping
    with open(ids_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            char = parts[1]
            ids = parts[2]
            if len(char) != 1:
                continue
            first = ids[0] if ids else ""
            if first in _LR:
                mapping[char] = "a"
            elif first in _UD:
                mapping[char] = "s"
            elif first in _WRAP:
                mapping[char] = "d"
            else:
                mapping[char] = "f"
    print(f"IDS 结构数据已加载：{len(mapping)} 字")
    return mapping
