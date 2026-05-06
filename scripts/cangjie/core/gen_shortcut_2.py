#!/usr/bin/env python3
"""
Wucang5 二简方案生成脚本
支持两种模式：
1. 传统模式 (gb_only=False): 允许长码字与“原主字”(全码=2)竞争。若长码字频次 > 原主频次 * 1.5，则生成简码。
2. GB2312 保护模式 (gb_only=True): 仅 GB2312 汉字有资格，且仅占据空槽（无 GB2312 原主）。
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
    is_han_char,
    REPO_ROOT
)

def is_gb2312(char: str) -> bool:
    """判断是否为 GB2312 范围内的汉字。"""
    if len(char) != 1 or not ('\u4e00' <= char <= '\u9fa5'):
        return False
    try:
        char.encode('gb2312')
        return True
    except UnicodeEncodeError:
        return False

def generate_shortcut_2(gb_only: bool = False, prefix: bool = True, count: int = 0, auto_coverage: float = 0.90, char_scores: dict[str, int] = None):
    source_dict = REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml"
    output_path = REPO_ROOT / "scripts/cangjie/prototypes/two_code.txt"

    # 1. 排除名单 (z 和 1)
    excluded_chars = set()
    for f_name in ["z_code.txt", "one_code.txt"]:
        p = REPO_ROOT / "scripts/cangjie/prototypes" / f_name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 1 and parts[0] and not parts[0].startswith("#"):
                        excluded_chars.add(parts[0])

    # 2. 获取加权得分
    if char_scores is None:
        char_scores = get_weighted_frequencies()

    raw_entries = parse_cangjie_dict(source_dict)
    char_codes = {}
    for e in raw_entries:
        if not is_han_char(e.text) or e.code.startswith('z') or e.code.startswith('x'): continue
        if e.text in excluded_chars: continue
        # 记录每个字的最短编码
        if e.text not in char_codes or len(e.code) < len(char_codes[e.text]):
            char_codes[e.text] = e.code

    # 3. 分组候选
    candidates_by_code = defaultdict(lambda: {"orig": None, "long": []})
    for char, full_code in char_codes.items():
        score = char_scores.get(char, 0)
        if score <= 0: continue
        
        if len(full_code) == 2:
            # 只有当 gb_only 为 False，或者原主是 GB2312 时，才记录原主用于保护/竞争
            if not gb_only or is_gb2312(char):
                curr_orig = candidates_by_code[full_code]["orig"]
                if not curr_orig or score > curr_orig[1]:
                    candidates_by_code[full_code]["orig"] = (char, score)
        elif len(full_code) > 2:
            if gb_only and not is_gb2312(char): continue
            code2 = full_code[:2] if prefix else full_code[0] + full_code[-1]
            candidates_by_code[code2]["long"].append((char, score))

    # 4. 判定
    valid_shortcuts = []
    for code2, data in candidates_by_code.items():
        if not data["long"]: continue
        
        best_long = max(data["long"], key=lambda x: x[1])
        long_char, long_score = best_long
        
        threshold = 0
        if data["orig"]:
            if gb_only:
                threshold = float('inf') # GB2312 绝对保护
            else:
                threshold = data["orig"][1] * 1.5 # 1.5 倍竞争
            
        if long_score > threshold:
            valid_shortcuts.append((long_char, code2, long_score))

    # 5. 过滤与输出
    valid_shortcuts.sort(key=lambda x: x[2], reverse=True)
    
    if count > 0:
        top_n = valid_shortcuts[:count]
    else:
        # 自动计算累计覆盖率阈值 (按全局字频分布计算)
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
        f.write("# 二简\n")
        for char, code, _ in top_n:
            f.write(f"{char}\t{code}\n")
    
    print(f"二简生成完成: {output_path} (数量: {len(top_n)})")

def main():
    parser = argparse.ArgumentParser(description="Wucang5 二简生成脚本")
    parser.add_argument("--gb-only", action="store_true", default=False)
    parser.add_argument("--prefix", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--count", type=int, default=0)
    parser.add_argument("--auto-coverage", type=float, default=0.90)
    args = parser.parse_args()
    generate_shortcut_2(gb_only=args.gb_only, prefix=args.prefix, count=args.count, auto_coverage=args.auto_coverage)

if __name__ == "__main__":
    main()
