#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.cangjie.core.cangjie_builder import (
    get_weighted_frequencies,
    is_han_char,
    parse_cangjie_dict,
)
from scripts.lingcang.core.mapping import DEFAULT_B_ZONE_MAP, project_cangjie4
from scripts.lingcang.core.paths import SOURCE_DICT


ROOTS = "abcdefghijklmnopqrstuvwxy"
VOWEL_ROOTS = "aeiou"
A_KEYS = "bcdfghjklmnpqrstvwxyz"


def load_rows(limit: int | None) -> list[tuple[str, str, int]]:
    scores = get_weighted_frequencies()
    best_by_char: dict[str, tuple[str, int]] = {}
    for entry in parse_cangjie_dict(SOURCE_DICT):
        if not is_han_char(entry.text):
            continue
        if entry.code.startswith(("x", "z")):
            continue
        code = project_cangjie4(entry.code)
        if any(ch not in ROOTS for ch in code):
            continue
        score = scores.get(entry.text, 0)
        current = best_by_char.get(entry.text)
        if current is None or score > current[1] or (score == current[1] and len(code) < len(current[0])):
            best_by_char[entry.text] = (code, score)
    rows = [(char, code, score) for char, (code, score) in best_by_char.items() if score > 0]
    rows.sort(key=lambda item: (-item[2], item[0]))
    return rows[:limit] if limit else rows


def encode_with_merge(source_code: str, left: str, right: str, target: str, private_root: str = "") -> str:
    def map_a(root: str) -> str:
        if root == private_root:
            return "z"
        if root == left or root == right:
            return target
        if root in VOWEL_ROOTS:
            # Other vowel roots are assumed to be moved to unique non-conflicting
            # placeholders for pair-loss estimation.
            return root.upper()
        return root

    if len(source_code) < 4:
        return "".join(map_a(ch) for ch in source_code) + DEFAULT_B_ZONE_MAP[source_code[-1]]
    return "".join(map_a(ch) for ch in source_code)


def collision_loss(rows: list[tuple[str, str, int]], left: str, right: str, target: str, private_root: str = "") -> tuple[float, int, int]:
    groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for char, code, score in rows:
        groups[encode_with_merge(code, left, right, target, private_root)].append((char, score))

    total_weight = 0
    collision_weight = 0
    collision_chars = 0
    max_candidates = 0
    for group in groups.values():
        group.sort(key=lambda item: (-item[1], item[0]))
        max_candidates = max(max_candidates, len(group))
        if len(group) > 1:
            collision_chars += len(group)
        for index, (_, score) in enumerate(group):
            total_weight += score
            if index > 0:
                collision_weight += score
    permyriad = collision_weight / total_weight * 10000 if total_weight else 0.0
    return permyriad, max_candidates, collision_chars


def main() -> int:
    parser = argparse.ArgumentParser(description="评估灵仓 A 区两个仓颉根合并的代理损失")
    parser.add_argument("--sample", type=int, default=5000, help="按综合字频取前 N 字；0 表示全部有频字")
    parser.add_argument("--top", type=int, default=80, help="输出低损失前 N 对")
    parser.add_argument("--targets", default=A_KEYS, help="可作为合并目标的 A 区键")
    args = parser.parse_args()

    rows = load_rows(None if args.sample == 0 else args.sample)
    results: list[tuple[float, int, int, str, str, str]] = []
    targets = [target for target in args.targets if target in A_KEYS]
    for vowel in VOWEL_ROOTS:
        for other in ROOTS:
            if other == vowel:
                continue
            allowed_targets = [target for target in targets if target == other or target not in VOWEL_ROOTS]
            for target in allowed_targets:
                # In normal use a merge target is the existing non-vowel root's key.
                if target != other and other not in VOWEL_ROOTS:
                    continue
                loss, max_candidates, collision_chars = collision_loss(rows, vowel, other, target)
                results.append((loss, max_candidates, collision_chars, vowel, other, target))

    results.sort()
    print(f"sample={len(rows)} pairs={len(results)}")
    print("rank\tloss\tmax\tcollision_chars\tmerge")
    for index, (loss, max_candidates, collision_chars, vowel, other, target) in enumerate(results[:args.top], start=1):
        print(f"{index}\t{loss:.2f}\t{max_candidates}\t{collision_chars}\t{vowel}/{other}->{target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
