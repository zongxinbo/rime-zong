#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from scripts.cangjie.core.cangjie_builder import (
    gb2312_level,
    get_weighted_frequencies,
    is_han_char,
    parse_cangjie_dict,
)
from scripts.lingcang.core.mapping import A_KEYS, B_KEYS, DEFAULT_A_ZONE_MAP, DEFAULT_B_ZONE_MAP, encode_lingcang, project_cangjie4
from scripts.lingcang.core.paths import SOURCE_DICT


PROTOTYPE_DIR = Path(__file__).resolve().parent / "prototypes"
ONE_CODE_PATH = PROTOTYPE_DIR / "one_code.txt"
TWO_CODE_PATH = PROTOTYPE_DIR / "two_code.txt"

ONE_CODES = {
    "了": "a",
    "是": "i",
    "的": "e",
    "我": "o",
    "不": "u",
}

ROOTS = "abcdefghijklmnopqrstuvwxy"


@dataclass(frozen=True)
class ShortcutCandidate:
    text: str
    code: str
    full_code: str
    score: int
    saved_keys: int
    net_score: int


def _best_lingcang_codes(char_scores: dict[str, int]) -> dict[str, tuple[str, str]]:
    best: dict[str, tuple[str, str]] = {}
    for entry in parse_cangjie_dict(SOURCE_DICT):
        if not is_han_char(entry.text):
            continue
        if entry.code.startswith(("x", "z")):
            continue
        projected = project_cangjie4(entry.code)
        try:
            code = encode_lingcang(entry.code)
        except KeyError:
            continue
        current = best.get(entry.text)
        if current is None:
            best[entry.text] = (projected, code)
            continue
        _, current_code = current
        current_score = (len(current_code), current_code, -char_scores.get(entry.text, 0))
        new_score = (len(code), code, -char_scores.get(entry.text, 0))
        if new_score < current_score:
            best[entry.text] = (projected, code)
    return best


def _shortcut_2_code(projected_source_code: str) -> str:
    return encode_lingcang(projected_source_code[0])[:1] + DEFAULT_B_ZONE_MAP[projected_source_code[-1]]


def root_slots() -> set[str]:
    return {DEFAULT_A_ZONE_MAP[root] + DEFAULT_B_ZONE_MAP[root] for root in ROOTS}


def available_two_code_slots() -> set[str]:
    return {a_key + b_key for a_key in A_KEYS for b_key in B_KEYS} - root_slots()


def generate_one_code() -> list[tuple[str, str]]:
    return sorted(ONE_CODES.items(), key=lambda item: item[1])


def generate_two_code(
    *,
    count: int,
    min_score: int,
    char_scores: dict[str, int] | None = None,
) -> list[ShortcutCandidate]:
    if char_scores is None:
        char_scores = get_weighted_frequencies()

    excluded_chars = set(ONE_CODES)
    best_codes = _best_lingcang_codes(char_scores)
    available_slots = available_two_code_slots()

    best_by_short_code: dict[str, ShortcutCandidate] = {}
    for char, (projected, full_code) in best_codes.items():
        if char in excluded_chars:
            continue
        if gb2312_level(char) != 1:
            continue
        score = char_scores.get(char, 0)
        if score < min_score:
            continue
        saved_keys = len(full_code) - 2
        if saved_keys <= 0:
            continue
        shortcut_code = _shortcut_2_code(projected)
        if shortcut_code not in available_slots:
            continue
        net_score = score * saved_keys
        candidate = ShortcutCandidate(char, shortcut_code, full_code, score, saved_keys, net_score)
        current = best_by_short_code.get(shortcut_code)
        if current is None or (candidate.score, candidate.saved_keys, candidate.net_score) > (
            current.score,
            current.saved_keys,
            current.net_score,
        ):
            best_by_short_code[shortcut_code] = candidate

    candidates = sorted(best_by_short_code.values(), key=lambda item: (-item.score, -item.saved_keys, item.code, item.text))
    if count > 0:
        candidates = candidates[:count]
    return sorted(candidates, key=lambda item: item.code)


def write_prototypes(one_codes: list[tuple[str, str]], two_codes: list[ShortcutCandidate]) -> None:
    PROTOTYPE_DIR.mkdir(parents=True, exist_ok=True)
    ONE_CODE_PATH.write_text(
        "# 灵仓一简：A/E/I/O/U 上屏码\n"
        + "".join(f"{char}\t{code}\n" for char, code in one_codes),
        encoding="utf-8",
        newline="\n",
    )
    TWO_CODE_PATH.write_text(
        "# 灵仓二简：首码 + 末根韵码；仅收高频 GB2312 一级字\n"
        "# 格式：字\t简码\t全码\t综合字频\t省码数\t净收益\n"
        + "".join(
            f"{item.text}\t{item.code}\t{item.full_code}\t{item.score}\t{item.saved_keys}\t{item.net_score}\n"
            for item in two_codes
        ),
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="生成灵仓一简/二简原型")
    parser.add_argument("--count", type=int, default=0, help="二简数量上限；0 表示按可用二简码位自动填满")
    parser.add_argument("--min-score", type=int, default=100000, help="二简最低综合字频")
    args = parser.parse_args()

    one_codes = generate_one_code()
    count = args.count or len(available_two_code_slots())
    two_codes = generate_two_code(count=count, min_score=args.min_score)
    write_prototypes(one_codes, two_codes)
    print(f"一简={len(one_codes)} 输出={ONE_CODE_PATH}")
    print(f"二简={len(two_codes)} 输出={TWO_CODE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
