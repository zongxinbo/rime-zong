#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.lingcang.core.evaluator import evaluate_mapping
from scripts.lingcang.core.mapping import DEFAULT_A_ZONE_MAP


def with_pairs(pairs: list[tuple[str, str, str]], moves: dict[str, str] | None = None) -> dict[str, str]:
    mapping = {ch: ch for ch in "bcdfghjklmnpqrstvwxy"}
    if moves:
        mapping.update(moves)
    for left, right, target in pairs:
        mapping[left] = target
        mapping[right] = target
    return mapping


SCHEMES: dict[str, dict[str, str]] = {
    "current": DEFAULT_A_ZONE_MAP,
    "edge_pairs": with_pairs(
        [
            ("e", "x", "x"),  # 水/難
            ("i", "y", "y"),  # 戈/卜
            ("o", "v", "v"),  # 人/女
            ("u", "t", "t"),  # 山/廿
        ],
        {"a": "z"},
    ),
    "avoid_t_merge": with_pairs(
        [
            ("e", "x", "x"),
            ("i", "y", "y"),
            ("o", "v", "v"),
            ("u", "w", "w"),  # 山/田
        ],
        {"a": "z"},
    ),
    "avoid_v_merge": with_pairs(
        [
            ("e", "x", "x"),
            ("i", "y", "y"),
            ("o", "r", "r"),  # 人/口
            ("u", "t", "t"),
        ],
        {"a": "z", "v": "v"},
    ),
    "merge_s_x": with_pairs(
        [
            ("e", "x", "x"),  # 水/難
            ("i", "y", "y"),  # 戈/卜
            ("u", "s", "s"),  # 山/尸
        ],
        {"a": "z", "o": "v"},
    ),
}


def main() -> int:
    rows = [evaluate_mapping(name, mapping) for name, mapping in SCHEMES.items()]
    rows.sort(key=lambda row: (row.zhihu_proxy_collision_permyriad, row.gb2312_avg_candidates, row.collision_chars))
    print("name\tentries\tunique\tcollision_groups\tcollision_chars\tgb_max\tgb_avg\tproxy_permyriad\tskipped")
    for row in rows:
        print(
            f"{row.name}\t{row.entries}\t{row.unique_codes}\t{row.collision_groups}\t"
            f"{row.collision_chars}\t{row.gb2312_max_candidates}\t{row.gb2312_avg_candidates:.3f}\t"
            f"{row.zhihu_proxy_collision_permyriad:.2f}\t{row.skipped_unknown_code}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
