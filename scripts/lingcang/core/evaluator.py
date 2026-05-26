from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from scripts.cangjie.core.cangjie_builder import (
    get_weighted_frequencies,
    is_gb2312,
    is_han_char,
    parse_cangjie_dict,
)

from .mapping import DEFAULT_B_ZONE_MAP, encode_with_maps
from .paths import SOURCE_DICT


@dataclass(frozen=True)
class MappingStats:
    name: str
    entries: int
    unique_codes: int
    collision_groups: int
    collision_chars: int
    gb2312_max_candidates: int
    gb2312_avg_candidates: float
    zhihu_proxy_collision_permyriad: float
    skipped_unknown_code: int


def evaluate_mapping(name: str, a_zone_map: dict[str, str]) -> MappingStats:
    scores = get_weighted_frequencies()
    entries = parse_cangjie_dict(SOURCE_DICT)
    code_groups: dict[str, list[str]] = defaultdict(list)
    code_seen_chars: dict[str, set[str]] = defaultdict(set)
    skipped_unknown_code = 0

    for entry in entries:
        if not is_han_char(entry.text):
            continue
        if entry.code.startswith(("z", "x")):
            continue
        try:
            code = encode_with_maps(entry.code, a_zone_map, DEFAULT_B_ZONE_MAP)
        except KeyError:
            skipped_unknown_code += 1
            continue
        if entry.text in code_seen_chars[code]:
            continue
        code_seen_chars[code].add(entry.text)
        code_groups[code].append(entry.text)

    collision_groups = [chars for chars in code_groups.values() if len(chars) > 1]
    gb_groups = [[char for char in chars if is_gb2312(char)] for chars in code_groups.values()]
    gb_groups = [chars for chars in gb_groups if chars]
    gb_max = max((len(chars) for chars in gb_groups), default=0)
    gb_avg = sum(len(chars) for chars in gb_groups) / len(gb_groups) if gb_groups else 0.0

    total_weight = 0
    collision_weight = 0
    for chars in code_groups.values():
        scored = sorted(chars, key=lambda char: (-scores.get(char, 0), char))
        for rank, char in enumerate(scored):
            weight = scores.get(char, 0)
            total_weight += weight
            if rank > 0:
                collision_weight += weight
    proxy = collision_weight / total_weight * 10000 if total_weight else 0.0

    return MappingStats(
        name=name,
        entries=sum(len(chars) for chars in code_groups.values()),
        unique_codes=len(code_groups),
        collision_groups=len(collision_groups),
        collision_chars=sum(len(chars) for chars in collision_groups),
        gb2312_max_candidates=gb_max,
        gb2312_avg_candidates=gb_avg,
        zhihu_proxy_collision_permyriad=proxy,
        skipped_unknown_code=skipped_unknown_code,
    )
