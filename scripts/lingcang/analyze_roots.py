#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.cangjie.core.cangjie_builder import (
    get_weighted_frequencies,
    is_han_char,
    parse_cangjie_dict,
)
from scripts.lingcang.core.mapping import project_cangjie4
from scripts.lingcang.core.paths import SOURCE_DICT


ROOT_NAMES = {
    "a": "日", "b": "月", "c": "金", "d": "木", "e": "水",
    "f": "火", "g": "土", "h": "竹", "i": "戈", "j": "十",
    "k": "大", "l": "中", "m": "一", "n": "弓", "o": "人",
    "p": "心", "q": "手", "r": "口", "s": "尸", "t": "廿",
    "u": "山", "v": "女", "w": "田", "x": "難", "y": "卜",
}


def main() -> int:
    scores = get_weighted_frequencies()
    entries = parse_cangjie_dict(SOURCE_DICT)
    raw_counts: Counter[str] = Counter()
    weighted_counts: Counter[str] = Counter()
    position_counts: dict[int, Counter[str]] = defaultdict(Counter)
    weighted_position_counts: dict[int, Counter[str]] = defaultdict(Counter)
    skipped_prefix = 0
    skipped_unknown = 0

    for entry in entries:
        if not is_han_char(entry.text):
            continue
        if entry.code.startswith(("x", "z")):
            skipped_prefix += 1
            continue
        projected = project_cangjie4(entry.code)
        if any(ch not in ROOT_NAMES for ch in projected):
            skipped_unknown += 1
            continue
        weight = scores.get(entry.text, 0)
        for index, root in enumerate(projected, start=1):
            raw_counts[root] += 1
            weighted_counts[root] += weight
            position_counts[index][root] += 1
            weighted_position_counts[index][root] += weight

    print(f"skipped_prefix={skipped_prefix} skipped_unknown={skipped_unknown}")
    print("root\tname\traw\tweighted\tpos1_w\tpos2_w\tpos3_w\tpos4_w")
    for root, weighted in weighted_counts.most_common():
        print(
            f"{root}\t{ROOT_NAMES[root]}\t{raw_counts[root]}\t{weighted}\t"
            f"{weighted_position_counts[1][root]}\t"
            f"{weighted_position_counts[2][root]}\t"
            f"{weighted_position_counts[3][root]}\t"
            f"{weighted_position_counts[4][root]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
