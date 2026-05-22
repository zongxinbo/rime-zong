#!/usr/bin/env python3
"""
Wucang5 三简方案生成脚本
支持两种模式：
1. 原生码位保护模式（默认）：长码字只占空槽，不抢已有三码全码字。
2. GB2312 保护模式 (gb_only=True): 仅 GB2312 汉字有资格，且仅占据空槽（无 GB2312 原主）。
3. 关闭保护时：允许长码字与“原主字”(全码=3)竞争，按省码收益扣除原主代价后排序。
"""

import sys
from pathlib import Path
from collections import defaultdict
import argparse

sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.cangjie_builder import (
    parse_cangjie_dict,
    parse_frequency_file,
    get_weighted_frequencies,
    is_gb2312,
    is_han_char,
    REPO_ROOT
)

NATIVE_3_PENALTY_RATIO = 1.2


def _load_excluded_chars_and_occupied_codes() -> tuple[set[str], set[str]]:
    """加载已有更短简码字，并保护同长度的既有码位。"""
    excluded_chars = set()
    occupied_codes = set()
    for f_name in ["z_code.txt", "one_code.txt", "two_code.txt"]:
        p = REPO_ROOT / "scripts/cangjie/prototypes" / f_name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 1 and parts[0] and not parts[0].startswith("#"):
                        excluded_chars.add(parts[0])
                    if len(parts) == 2 and len(parts[1]) == 3:
                        occupied_codes.add(parts[1])
    return excluded_chars, occupied_codes


def generate_shortcut_3(gb_only: bool = False, prefix: bool = True, count: int = 0, auto_coverage: float = 0.90, char_scores: dict[str, int] = None, protect_native: bool = True):
    source_dict = REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml"
    output_path = REPO_ROOT / "scripts/cangjie/prototypes/three_code.txt"

    # 1. 排除名单 (z, 1, 2)，并保护既有三码简码位。
    excluded_chars, occupied_codes = _load_excluded_chars_and_occupied_codes()

    # 2. 获取加权得分
    if char_scores is None:
        char_scores = get_weighted_frequencies()

    raw_entries = parse_cangjie_dict(source_dict)
    char_codes = {}
    for e in raw_entries:
        if not is_han_char(e.text) or e.code.startswith('z') or e.code.startswith('x'): continue
        if e.text in excluded_chars: continue
        if e.text not in char_codes or len(e.code) < len(char_codes[e.text]):
            char_codes[e.text] = e.code
    
    # 3. 分组候选
    candidates_by_code = defaultdict(lambda: {"orig": None, "long": []})
    for char, full_code in char_codes.items():
        if len(full_code) == 3:
            if not gb_only or is_gb2312(char):
                curr_orig = candidates_by_code[full_code]["orig"]
                score = char_scores.get(char, 0)
                if not curr_orig or score > curr_orig[1]:
                    candidates_by_code[full_code]["orig"] = (char, score)
        elif len(full_code) > 3:
            score = char_scores.get(char, 0)
            if score <= 0: continue
            if gb_only and not is_gb2312(char): continue
            code3 = full_code[:3] if prefix else full_code[0] + full_code[1] + full_code[-1]
            candidates_by_code[code3]["long"].append((char, score, len(full_code)))

    # 4. 按净收益判定：省码收益 - 原生码位代价。
    valid_shortcuts = []
    for code3, data in candidates_by_code.items():
        if code3 in occupied_codes:
            continue
        if not data["long"]:
            continue

        native_penalty = 0
        if data["orig"]:
            if gb_only or protect_native:
                continue
            else:
                native_penalty = data["orig"][1] * NATIVE_3_PENALTY_RATIO

        best_item = None
        for long_char, long_score, full_len in data["long"]:
            saved_keys = full_len - 3
            if saved_keys <= 0:
                continue
            net_score = long_score * saved_keys - native_penalty
            if net_score <= 0:
                continue
            item = (long_char, code3, long_score, net_score, saved_keys)
            if best_item is None or item[3] > best_item[3]:
                best_item = item

        if best_item is not None:
            valid_shortcuts.append(best_item)

    # 5. 过滤与输出
    valid_shortcuts.sort(key=lambda x: x[3], reverse=True)
    
    if count > 0:
        top_n = valid_shortcuts[:count]
    else:
        sorted_scores = sorted(char_scores.values(), reverse=True)
        total_score = sum(sorted_scores)
        cum_sum = 0
        threshold_score = 0
        for s in sorted_scores:
            cum_sum += s
            if cum_sum >= total_score * auto_coverage:
                threshold_score = s
                break
        top_n = [item for item in valid_shortcuts if item[2] >= threshold_score]
        
    top_n.sort(key=lambda x: x[1])

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 三简\n")
        for char, code, *_ in top_n:
            f.write(f"{char}\t{code}\n")
    
    print(f"三简生成完成: {output_path} (数量: {len(top_n)})")

def main():
    parser = argparse.ArgumentParser(description="Wucang5 三简生成脚本")
    parser.add_argument("--gb-only", action="store_true", default=False)
    parser.add_argument("--prefix", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--count", type=int, default=0)
    parser.add_argument("--auto-coverage", type=float, default=0.90)
    parser.add_argument("--protect-native", action=argparse.BooleanOptionalAction, default=True,
                        help="保护已有三码全码位，不让长码字抢位")
    args = parser.parse_args()
    generate_shortcut_3(gb_only=args.gb_only, prefix=args.prefix, count=args.count, auto_coverage=args.auto_coverage, protect_native=args.protect_native)

if __name__ == "__main__":
    main()
