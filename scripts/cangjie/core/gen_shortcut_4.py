#!/usr/bin/env python3
"""Wucang5 四简方案生成脚本。

默认生成“平衡版”GB 四简：
  1. 对象：GB2312 一级字，或达到频率门槛的 GB2312 二级字；
  2. 取码：full_code[:4]；
  3. 四简码位内部去重，同字只保留一个四简；
  4. 压到原生四码位时，按省码收益扣除原主代价后判定。
"""

import sys
from pathlib import Path
from collections import defaultdict
import argparse

sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.cangjie_builder import (
    CANGJIE5_DICT_PATH,
    FOUR_CODE_PATH,
    ONE_CODE_PATH,
    parse_cangjie_dict,
    get_weighted_frequencies,
    gb2312_level,
    is_han_char,
    THREE_CODE_PATH,
    TWO_CODE_PATH,
    Z_CODE_PATH,
)

BALANCED_NATIVE4_RATIO = 3.0
DEFAULT_LEVEL2_MIN_SCORE = 1000


def _load_excluded_chars() -> set[str]:
    """加载已经获得更短码的字，四简不再重复发放。"""
    excluded_chars = set()
    for p in [Z_CODE_PATH, ONE_CODE_PATH, TWO_CODE_PATH, THREE_CODE_PATH]:
        if not p.exists():
            continue
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) >= 1 and parts[0] and not parts[0].startswith("#"):
                    excluded_chars.add(parts[0])
    return excluded_chars


def generate_shortcut_4(
    mode: str = "balanced",
    count: int = 0,
    level2_min_score: int | float = DEFAULT_LEVEL2_MIN_SCORE,
    char_scores: dict[str, int | float] | None = None,
):
    source_dict = CANGJIE5_DICT_PATH
    output_path = FOUR_CODE_PATH

    if mode not in {"safe", "balanced", "aggressive"}:
        raise ValueError(f"未知四简模式: {mode}")
    if count < 0:
        raise ValueError("--s4-count 不能为负数")
    if level2_min_score < 0:
        raise ValueError("--s4-level2-min-score 不能为负数")

    excluded_chars = _load_excluded_chars()
    if char_scores is None:
        char_scores = get_weighted_frequencies()

    raw_entries = parse_cangjie_dict(source_dict)

    native4_chars = defaultdict(set)
    for e in raw_entries:
        if not is_han_char(e.text) or e.code.startswith('z') or e.code.startswith('x'):
            continue
        if len(e.code) == 4:
            native4_chars[e.code].add(e.text)

    candidates = []
    filtered_level2 = 0
    for e in raw_entries:
        if not is_han_char(e.text) or e.code.startswith('z') or e.code.startswith('x'):
            continue
        if e.text in excluded_chars:
            continue
        # 四简默认处理 GB2312 一级字；二级字需要频率证明，避免冷僻字大量进入四简层。
        level = gb2312_level(e.text)
        if level is None:
            continue
        score = char_scores.get(e.text, 0)
        if level == 2 and score < level2_min_score:
            filtered_level2 += 1
            continue
        if len(e.code) == 5:
            code4 = e.code[:4]
            conflicts = {ch for ch in native4_chars.get(code4, set()) if ch != e.text}
            candidates.append({
                "char": e.text,
                "code": code4,
                "score": score,
                "net_score": score,
                "conflicts": conflicts,
                "full_code": e.code,
                "level": level,
            })

    rejected_native = 0
    allowed_native = 0

    if mode == "aggressive":
        selected = candidates
    else:
        accepted = []
        for item in candidates:
            conflicts = item["conflicts"]
            if not conflicts:
                accepted.append(item)
                continue

            if mode == "safe":
                rejected_native += 1
                continue

            # 平衡版：如果原生四码字已经有更短简码，放行；否则按净收益竞争。
            active_conflicts = [ch for ch in conflicts if ch not in excluded_chars]
            max_conflict_score = max((char_scores.get(ch, 0) for ch in active_conflicts), default=0)
            net_score = item["score"] - max_conflict_score * BALANCED_NATIVE4_RATIO
            item["net_score"] = net_score
            if not active_conflicts or net_score > 0:
                allowed_native += 1
                accepted.append(item)
            else:
                rejected_native += 1

        # 每个四码位只保留一个最高价值字；同一个字也只保留一个四简。
        selected = []
        used_codes = set()
        used_chars = set()
        accepted.sort(key=lambda item: (
            -item["net_score"],
            len(item["conflicts"]),
            item["code"],
            item["char"],
        ))
        for item in accepted:
            if item["code"] in used_codes or item["char"] in used_chars:
                continue
            used_codes.add(item["code"])
            used_chars.add(item["char"])
            selected.append(item)

    if count > 0:
        selected.sort(key=lambda item: (-item["net_score"], item["code"], item["char"]))
        selected = selected[:count]

    selected.sort(key=lambda item: (item["code"], -item["net_score"], item["char"]))

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# 四简（{mode}，GB2312 五码字）\n")
        for item in selected:
            f.write(f"{item['char']}\t{item['code']}\n")

    dup_codes = len(selected) - len({item["code"] for item in selected})
    level1_count = sum(1 for item in selected if item["level"] == 1)
    level2_count = sum(1 for item in selected if item["level"] == 2)
    print(
        f"四简生成完成: {output_path} "
        f"(数量: {len(selected)} 模式: {mode} 重码位: {dup_codes} "
        f"一级字: {level1_count} 二级字: {level2_count} 二级低频过滤: {filtered_level2} "
        f"原生四码放行: {allowed_native} 原生四码拒绝: {rejected_native})"
    )


def main():
    parser = argparse.ArgumentParser(description="Wucang5 四简生成脚本")
    parser.add_argument("--s4-mode", choices=["safe", "balanced", "aggressive"], default="balanced")
    parser.add_argument("--s4-count", type=int, default=0, help="四简数量限制；0 表示不限制")
    parser.add_argument("--s4-level2-min-score", type=float, default=DEFAULT_LEVEL2_MIN_SCORE,
                        help="GB2312 二级字进入四简的最低综合字频；0 表示不过滤二级字")
    args = parser.parse_args()
    generate_shortcut_4(
        mode=args.s4_mode,
        count=args.s4_count,
        level2_min_score=args.s4_level2_min_score,
    )


if __name__ == "__main__":
    main()
