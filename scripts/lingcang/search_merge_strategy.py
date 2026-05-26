#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import sys
from collections import defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.lingcang.analyze_merge_pairs import (
    ROOTS,
    VOWEL_ROOTS,
    collision_loss,
    load_rows,
)
from scripts.lingcang.core.mapping import DEFAULT_B_ZONE_MAP


EXISTING_A_ROOTS = tuple(root for root in ROOTS if root not in VOWEL_ROOTS)


def build_pair_tables(rows: list[tuple[str, str, int]]) -> tuple[dict[str, list[str]], dict[tuple[str, str], float]]:
    choices: dict[str, list[str]] = {}
    costs: dict[tuple[str, str], float] = {}
    for vowel in VOWEL_ROOTS:
        ranked = []
        for target in EXISTING_A_ROOTS:
            loss, _, _ = collision_loss(rows, vowel, target, target)
            costs[(vowel, target)] = loss
            ranked.append((loss, target))
        ranked.sort()
        choices[vowel] = [target for _, target in ranked]
        costs[(vowel, "z")] = 0.0

    for left, right in itertools.combinations(VOWEL_ROOTS, 2):
        loss, _, _ = collision_loss(rows, left, right, "z")
        costs[(left + right, "z")] = loss
    return choices, costs


def approximate_loss(assignment: dict[str, str], costs: dict[tuple[str, str], float]) -> float:
    total = 0.0
    z_roots = []
    for vowel, target in assignment.items():
        if target == "z":
            z_roots.append(vowel)
        else:
            total += costs[(vowel, target)]
    for left, right in itertools.combinations(sorted(z_roots), 2):
        total += costs[(left + right, "z")]
    return total


def exact_loss(
    encoded_rows: list[tuple[str, tuple[str, ...], str, int]],
    assignment: dict[str, str],
) -> tuple[float, int, int]:
    mapping = {root: root for root in EXISTING_A_ROOTS}
    mapping.update(assignment)
    groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for char, roots, suffix, weight in encoded_rows:
        code = "".join(mapping[root] for root in roots) + suffix
        groups[code].append((char, weight))

    total_weight = 0
    collision_weight = 0
    collision_chars = 0
    max_candidates = 0
    for group in groups.values():
        group.sort(key=lambda item: (-item[1], item[0]))
        max_candidates = max(max_candidates, len(group))
        if len(group) > 1:
            collision_chars += len(group)
        for index, (_, weight) in enumerate(group):
            total_weight += weight
            if index:
                collision_weight += weight
    permyriad = collision_weight / total_weight * 10000 if total_weight else 0.0
    return permyriad, max_candidates, collision_chars


def iter_assignments(choices: dict[str, list[str]], per_vowel: int):
    vowels = tuple(VOWEL_ROOTS)
    choice_lists = [choices[vowel][:per_vowel] + ["z"] for vowel in vowels]
    for targets in itertools.product(*choice_lists):
        if "z" not in targets:
            continue
        existing_targets = [target for target in targets if target != "z"]
        if len(existing_targets) != len(set(existing_targets)):
            continue
        yield dict(zip(vowels, targets))


def main() -> int:
    parser = argparse.ArgumentParser(description="搜索灵仓 A 区元音根合并策略")
    parser.add_argument("--sample", type=int, default=5000, help="按综合字频取前 N 字；0 表示全部有频字")
    parser.add_argument("--per-vowel", type=int, default=14, help="每个元音根按二根损失保留的候选 A 键数")
    parser.add_argument("--exact-candidates", type=int, default=5000, help="近似排序后进入真实分桶评分的候选数")
    parser.add_argument("--top", type=int, default=40, help="输出前 N 个策略")
    args = parser.parse_args()

    rows = load_rows(None if args.sample == 0 else args.sample)
    choices, costs = build_pair_tables(rows)
    encoded_rows = [
        (char, tuple(code), DEFAULT_B_ZONE_MAP[code[-1]] if len(code) < 4 else "", weight)
        for char, code, weight in rows
    ]

    approximate: list[tuple[float, dict[str, str]]] = []
    for assignment in iter_assignments(choices, args.per_vowel):
        approximate.append((approximate_loss(assignment, costs), assignment))
    approximate.sort(key=lambda item: item[0])

    exact: list[tuple[tuple[float, int, int], dict[str, str]]] = []
    for _, assignment in approximate[: args.exact_candidates]:
        exact.append((exact_loss(encoded_rows, assignment), assignment))
    exact.sort(key=lambda item: (item[0], tuple(sorted(item[1].items()))))

    print(
        f"sample={len(rows)} approximate={len(approximate)} exact={min(args.exact_candidates, len(approximate))}"
    )
    print("rank\tloss\tmax\tcollision_chars\tassignment")
    for index, (stats, assignment) in enumerate(exact[: args.top], start=1):
        loss, max_candidates, collision_chars = stats
        assignment_text = " ".join(f"{root}->{target}" for root, target in sorted(assignment.items()))
        print(f"{index}\t{loss:.2f}\t{max_candidates}\t{collision_chars}\t{assignment_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
