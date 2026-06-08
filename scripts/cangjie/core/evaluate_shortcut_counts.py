#!/usr/bin/env python3
"""分析四仓五代二三简容量，避免反复生成词典。

脚本保留绝对空位统计，并增加参数化候选扫描，规则贴近
gen_sicang5.py 的二简、三简选取方式。动态选重率使用
scripts/assess/summary.py 中“简全联用-实际”同一套 mixed 评估模式。
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CANGJIE_DIR = SCRIPT_DIR.parent
REPO_ROOT = CANGJIE_DIR.parents[1]
ASSESS_DIR = REPO_ROOT / "scripts" / "assess"
sys.path.append(str(CANGJIE_DIR))
sys.path.append(str(ASSESS_DIR))

from core.cangjie_builder import (  # noqa: E402
    CANGJIE5_DICT_PATH,
    FIXED_PREFIX_CODE_PATH,
    ONE_CODE_PATH,
    ROOT_CODE_PATH,
    TWO_CODE_PATH,
    build_base_entries,
    build_dedup_prefix_entries,
    build_fullcode_entries,
    build_shortcut_leader_chars,
    build_z_suffix_entries,
    collect_char_full_codes,
    get_weighted_frequencies,
    is_common_han_char,
    load_shortcut_entries,
    parse_cangjie_dict,
    project_code,
)
from core.gen_shortcut_2 import collect_shortcut_2_candidates  # noqa: E402
from core.gen_shortcut_3 import collect_shortcut_3_candidates  # noqa: E402
from core.glyph_codes import get_glyph_preferred_codes  # noqa: E402
from core.paths import FREQ_PATHS  # noqa: E402
from core.weight_profiles import WEIGHT_PROFILES, get_weight_profile  # noqa: E402
from duplicate_analysis import analyze_duplicates  # noqa: E402
from utils import get_charset_filter, load_freq, merge_freq  # noqa: E402


LETTERS = "abcdefghijklmnopqrstuvwy"  # 保留 x/z 给救援层使用。
ASSESS_PROFILES = {
    "zhihu": ("Zhihu", "GB2312"),
    "blcu": ("BLCU", "GB2312"),
    "taiwan": ("Taiwan", "GUOZI"),
    "guji": ("Guji", "CJK_BASIC"),
    "combined": ("combined", "CJK_BASIC"),
}


@dataclass(frozen=True)
class ShortcutCandidate:
    level: int
    char: str
    code: str
    source_code: str
    score: int | float
    net_score: float
    saved_keys: int
    native_char: str | None
    native_score: int | float


def theoretical_codes(level: int) -> set[str]:
    if level == 2:
        return {a + b for a in LETTERS for b in LETTERS}
    if level == 3:
        return {a + b + c for a in LETTERS for b in LETTERS for c in LETTERS}
    raise ValueError("level 只能是 2 或 3")


def report_absolute_slots(entries) -> None:
    full_codes: dict[int, set[str]] = {2: set(), 3: set()}
    for entry in entries:
        if not is_common_han_char(entry.text):
            continue
        if entry.code.startswith(("z", "x")):
            continue
        if len(entry.code) in full_codes:
            full_codes[len(entry.code)].add(entry.code)

    print("--- 绝对空位 ---")
    for level in (2, 3):
        theoretical = theoretical_codes(level)
        empty = theoretical - full_codes[level]
        print(
            f"{level}码 理论={len(theoretical)} "
            f"原生占用={len(full_codes[level])} "
            f"绝对空位={len(empty)} "
            f"空位率={len(empty) / len(theoretical) * 100:.2f}%"
        )


def to_display_candidate(level: int, candidate) -> ShortcutCandidate:
    char, code, score, net_score, saved_keys, source_code, native_char, native_score = candidate
    return ShortcutCandidate(
        level=level,
        char=char,
        code=code,
        source_code=source_code,
        score=score,
        net_score=net_score,
        saved_keys=saved_keys,
        native_char=native_char,
        native_score=native_score,
    )


def collect_level_candidates(
    *,
    level: int,
    char_scores: dict[str, int],
    weights: str,
    prefix: bool,
    protect_native: bool,
    protect_native_charset: str,
    protect_native_min_score: float,
    shortcut_candidate_min_score: float,
    absolute_empty_only: bool,
) -> list[ShortcutCandidate]:
    """调用二三简生成器的候选收集逻辑，转成分析脚本展示用结构。"""
    common_args = {
        "prefix": prefix,
        "char_scores": char_scores,
        "protect_native": protect_native,
        "protect_native_charset": protect_native_charset,
        "protect_native_min_score": protect_native_min_score,
        "shortcut_candidate_min_score": shortcut_candidate_min_score,
        "weights": weights,
        "absolute_empty_only": absolute_empty_only,
    }
    if level == 2:
        return [to_display_candidate(2, item) for item in collect_shortcut_2_candidates(**common_args)]
    if level == 3:
        return [to_display_candidate(3, item) for item in collect_shortcut_3_candidates(**common_args)]
    raise ValueError("level 只能是 2 或 3")


def load_assess_freq(name: str) -> dict[str, float]:
    if name == "combined":
        blcu, _ = load_freq(str(FREQ_PATHS["BLCU"]))
        taiwan, _ = load_freq(str(FREQ_PATHS["Taiwan"]))
        merged, _ = merge_freq(blcu, taiwan)
        return merged
    path = FREQ_PATHS.get(name)
    if path is None:
        raise ValueError(f"评估字频只能是 {', '.join({value[0] for value in ASSESS_PROFILES.values()})}")
    norm, _ = load_freq(str(path))
    return norm


def build_sicang_assess_entries(
    selected: list[ShortcutCandidate],
    *,
    char_scores: dict[str, int],
    weights: str,
    dedup_layers: str,
):
    shortcut_entries, root_chars = load_shortcut_entries({
        "root": ROOT_CODE_PATH,
        1: ONE_CODE_PATH,
        "fixed_prefix": FIXED_PREFIX_CODE_PATH,
    })
    shortcut_entries.extend((item.char, item.code, item.level) for item in selected)

    char_full_codes = collect_char_full_codes(
        CANGJIE5_DICT_PATH,
        exclude_extended=False,
        only_first_full_code=False,
    )
    used_text_code = {(char, code) for char, code, _ in shortcut_entries}
    fullcode_entries = build_fullcode_entries(
        char_full_codes,
        root_chars=root_chars,
        used_text_code=used_text_code,
        char_freqs=char_scores,
        max_code_length=4,
    )
    all_entries = build_base_entries(
        shortcut_entries,
        fullcode_entries,
        char_freqs=char_scores,
        fullcode_yield=False,
        fullcode_yield_min_score=1000,
    )
    shortcut_leader_chars = build_shortcut_leader_chars(all_entries)

    preferred_codes = {
        text: project_code(code, 4)
        for text, code in get_glyph_preferred_codes(weights).items()
    }
    shortcut_source_entries = [
        entry
        for entry in all_entries
        if entry[1] < 5
        or entry[4] not in preferred_codes
        or entry[0] == preferred_codes[entry[4]]
    ]
    natural_shortcut_source_entries = list(shortcut_source_entries)
    natural_shortcut_leader_chars = set(shortcut_leader_chars)

    prefix_level2_scores = get_weighted_frequencies(get_weight_profile("sc"))
    prefix_level3_scores = get_weighted_frequencies(get_weight_profile("sc_daily"))
    prefix_full_scores = get_weighted_frequencies(get_weight_profile("sc_daily"))

    prefix_used_text_code = {(char, code) for char, code, _ in shortcut_entries}
    prefix_fullcode_entries = build_fullcode_entries(
        char_full_codes,
        root_chars=root_chars,
        used_text_code=prefix_used_text_code,
        char_freqs=char_scores,
        max_code_length=4,
    )
    prefix_all_entries = build_base_entries(
        shortcut_entries,
        prefix_fullcode_entries,
        char_freqs=char_scores,
        fullcode_yield=False,
        fullcode_yield_min_score=1000,
    )
    preferred_prefix_codes = {
        text: project_code(code, 4)
        for text, code in get_glyph_preferred_codes(weights).items()
    }
    shared_source_entries = [
        entry
        for entry in prefix_all_entries
        if entry[1] < 5
        or entry[4] not in preferred_prefix_codes
        or entry[0] == preferred_prefix_codes[entry[4]]
    ]
    shared_leader_chars = build_shortcut_leader_chars(prefix_all_entries)
    used_text_code_for_generated = set(used_text_code)
    if dedup_layers in {"prefix", "all"}:
        shared_entries_with_levels = build_dedup_prefix_entries(
            shared_source_entries,
            occupied_entries=shared_source_entries,
            used_text_code=used_text_code_for_generated,
            shortcut_leader_chars=shared_leader_chars,
            char_freqs=char_scores,
            short_level_char_freqs={
                2: prefix_level2_scores,
                3: prefix_level3_scores,
            },
            full_char_freqs=prefix_full_scores,
            max_code_length=4,
            charset="frequency",
            min_score=1,
            short=True,
            full=False,
            short_levels=(2, 3),
            full_source_length=4,
            deep_rank_multiplier=1.5,
        )
        shared_entries = [entry for _, entry in shared_entries_with_levels]
        all_entries.extend(shared_entries)
        all_entries.sort()
        shortcut_source_entries.extend(shared_entries)
        shortcut_source_entries.sort()
        shortcut_leader_chars = build_shortcut_leader_chars(all_entries)

        scheme_entries_with_levels = build_dedup_prefix_entries(
            shortcut_source_entries,
            occupied_entries=shortcut_source_entries,
            used_text_code=used_text_code_for_generated,
            shortcut_leader_chars=shortcut_leader_chars,
            char_freqs=char_scores,
            short_level_char_freqs={
                2: prefix_level2_scores,
                3: prefix_level3_scores,
            },
            full_char_freqs=prefix_full_scores,
            max_code_length=4,
            charset="frequency",
            min_score=1,
            short=False,
            full=True,
            short_levels=(),
            full_source_length=4,
            deep_rank_multiplier=1.5,
        )
        scheme_entries = [entry for _, entry in scheme_entries_with_levels]
        if scheme_entries:
            all_entries.extend(scheme_entries)
            all_entries.sort()
            shortcut_source_entries.extend(scheme_entries)
            shortcut_source_entries.sort()

    if dedup_layers in {"suffix", "all"}:
        suffix_entries = build_z_suffix_entries(
            natural_shortcut_source_entries,
            occupied_entries=all_entries,
            used_text_code=used_text_code_for_generated,
            shortcut_leader_chars=natural_shortcut_leader_chars,
            char_freqs=char_scores,
            max_code_length=4,
            charset="frequency",
            min_score=1,
            rank_suffixes=((2, "z"), (3, "x")),
            max_source_length=3,
            occupied_policy="ignore-nonfrequency-or-shortcut",
        )
        all_entries.extend(suffix_entries)
        all_entries.sort()

    return [(char, code, char_scores.get(char, 0)) for code, _, _, _, char in all_entries]


def mixed_dynamic_rate(
    selected: list[ShortcutCandidate],
    *,
    assess_freq: dict[str, float],
    charset: str,
    char_scores: dict[str, int],
    weights: str,
    dedup_layers: str,
) -> float:
    rows = build_sicang_assess_entries(
        selected,
        char_scores=char_scores,
        weights=weights,
        dedup_layers=dedup_layers,
    )
    charset_filter = get_charset_filter(charset)
    result = analyze_duplicates(
        "",
        "",
        charset_filter=charset_filter,
        mode="mixed",
        _preloaded_freq=assess_freq,
        _preloaded_entries=rows,
    )
    return result["dynamic_rate"]


def parse_csv_numbers(text: str, *, cast=float) -> list:
    values = []
    for part in text.split(","):
        part = part.strip()
        if part:
            values.append(cast(part))
    return values


def print_candidate_summary(label: str, candidates: list[ShortcutCandidate]) -> None:
    native_conflicts = sum(1 for item in candidates if item.native_char is not None)
    print(
        f"{label}: 候选={len(candidates)} "
        f"抢原生码位={native_conflicts} "
        f"最高净收益={candidates[0].net_score if candidates else 0:.0f}"
    )


def main() -> None:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Sicang5 二三简容量与动态重码率分析")
    parser.add_argument("--level", choices=("2", "3", "both"), default="both", help="分析二简、三简或两者")
    parser.add_argument("--weights", choices=tuple(WEIGHT_PROFILES), default="sc_daily")
    parser.add_argument("--prefix", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--protect-native", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--protect-native-charset", choices=("all", "frequency", "gbk", "gb2312"), default="gbk")
    parser.add_argument("--protect-native-min-score", type=float, default=3000)
    parser.add_argument("--shortcut-candidate-min-score", type=float, default=3000)
    parser.add_argument("--absolute-empty-only", action=argparse.BooleanOptionalAction, default=False,
                        help="只允许绝对空位，不抢任何原生二三码位")
    parser.add_argument("--counts", default="300,500,800,1000,1200,1500,2000",
                        help="扫描候选数量列表")
    parser.add_argument("--min-scores", default="3000",
                        help="扫描入选最低分列表；每个值会重新生成候选池")
    parser.add_argument("--assess-profile", choices=tuple(ASSESS_PROFILES), default="combined",
                        help="动态选重率评估口径，自动使用与 summary.py 相同的字频和字符集")
    parser.add_argument("--dedup-layers", choices=("none", "prefix", "suffix", "all"), default="none",
                        help="动态选重率是否计入 z/x 前缀、后缀消重层；none 用于评估二三简本身，all 用于对齐最终方案")
    parser.add_argument("--top", type=int, default=8, help="打印前 N 个候选样例")
    args = parser.parse_args()

    report_absolute_slots(parse_cangjie_dict(CANGJIE5_DICT_PATH))

    levels = [2, 3] if args.level == "both" else [int(args.level)]
    counts = parse_csv_numbers(args.counts, cast=int)
    min_scores = parse_csv_numbers(args.min_scores, cast=float)
    char_scores = get_weighted_frequencies(get_weight_profile(args.weights))
    assess_freq_name, assess_charset = ASSESS_PROFILES[args.assess_profile]
    assess_freq = load_assess_freq(assess_freq_name)

    print("\n--- 参数化候选与简全联用动态选重率 ---")
    print(
        f"权重={args.weights} 保护原生码={args.protect_native} "
        f"保护字符集={args.protect_native_charset} 保护最低分={args.protect_native_min_score:g} "
        f"仅绝对空位={args.absolute_empty_only} 评估口径={args.assess_profile} "
        f"评估字频={assess_freq_name} 评估字符集={assess_charset} 消重层={args.dedup_layers}"
    )

    for min_score in min_scores:
        print(f"\n[简码候选最低分={min_score:g}]")
        selected_by_level: dict[int, list[ShortcutCandidate]] = {}
        for level in levels:
            candidates = collect_level_candidates(
                level=level,
                char_scores=char_scores,
                weights=args.weights,
                prefix=args.prefix,
                protect_native=args.protect_native,
                protect_native_charset=args.protect_native_charset,
                protect_native_min_score=args.protect_native_min_score,
                shortcut_candidate_min_score=min_score,
                absolute_empty_only=args.absolute_empty_only,
            )
            selected_by_level[level] = candidates
            print_candidate_summary(f"{level}简", candidates)
            for item in candidates[: args.top]:
                native = f" 原生={item.native_char}:{item.native_score:g}" if item.native_char else ""
                print(
                    f"  {item.char}\t{item.code}\t来源={item.source_code} "
                    f"分数={item.score:g} 净收益={item.net_score:.0f}{native}"
                )

        print("\n| 数量 | 二简 | 三简 | 简全联用动态选重率 |")
        print("| ---: | ---: | ---: | ---: |")
        for count in counts:
            selected: list[ShortcutCandidate] = []
            s2 = selected_by_level.get(2, [])[:count if 2 in levels else 0]
            s3 = selected_by_level.get(3, [])[:count if 3 in levels else 0]
            selected.extend(s2)
            selected.extend(s3)
            rate = mixed_dynamic_rate(
                selected,
                assess_freq=assess_freq,
                charset=assess_charset,
                char_scores=char_scores,
                weights=args.weights,
                dedup_layers=args.dedup_layers,
            )
            print(f"| {count} | {len(s2)} | {len(s3)} | {rate * 10000:.2f}‱ |")


if __name__ == "__main__":
    main()
