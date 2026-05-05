#!/usr/bin/env python3
"""
Wucang5 三简方案生成脚本
支持两种模式：
1. 传统模式 (gb_only=False): 允许长码字与“原主字”(全码=3)竞争。若长码字频次 > 原主频次 * 1.2，则生成简码。
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

def generate_shortcut_3(gb_only: bool = False, prefix: bool = True, count: int = 0, auto_coverage: float = 0.90):
    source_dict = REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml"
    output_path = REPO_ROOT / "scripts/cangjie/prototypes/three_code.txt"

    # 1. 排除名单 (z, 1, 2)
    excluded_chars = set()
    for f_name in ["z_code.txt", "one_code.txt", "two_code.txt"]:
        p = REPO_ROOT / "scripts/cangjie/prototypes" / f_name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 1 and parts[0] and not parts[0].startswith("#"):
                        excluded_chars.add(parts[0])

    # 2. 计算得分
    weights = {"Dialogue": 6, "Subtlex": 5, "Zhihu": 4, "BLCU": 2, "Essay": 1}
    freq_paths = {
        "Dialogue": REPO_ROOT / "schemas/frequency/char/dialogue_char_freq.txt",
        "Subtlex": REPO_ROOT / "schemas/frequency/char/subtlex_char_freq.txt",
        "Zhihu": REPO_ROOT / "schemas/frequency/char/zhihu_char_freq.txt",
        "BLCU": REPO_ROOT / "schemas/frequency/char/blcu_char_freq.txt",
        "Essay": REPO_ROOT / "schemas/common/essay-zh-hans.txt"
    }
    char_scores = defaultdict(int)
    for name, path in freq_paths.items():
        if path.exists():
            freqs, _ = parse_frequency_file(path)
            for char, val in freqs.items():
                char_scores[char] += val * weights[name]

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
        score = char_scores.get(char, 0)
        if score <= 0: continue
        
        if len(full_code) == 3:
            if not gb_only or is_gb2312(char):
                curr_orig = candidates_by_code[full_code]["orig"]
                if not curr_orig or score > curr_orig[1]:
                    candidates_by_code[full_code]["orig"] = (char, score)
        elif len(full_code) > 3:
            if gb_only and not is_gb2312(char): continue
            code3 = full_code[:3] if prefix else full_code[0] + full_code[1] + full_code[-1]
            candidates_by_code[code3]["long"].append((char, score))

    # 4. 判定
    valid_shortcuts = []
    for code3, data in candidates_by_code.items():
        if not data["long"]: continue
        
        best_long = max(data["long"], key=lambda x: x[1])
        long_char, long_score = best_long
        
        threshold = 0
        if data["orig"]:
            if gb_only:
                threshold = float('inf')
            else:
                threshold = data["orig"][1] * 1.2
            
        if long_score > threshold:
            valid_shortcuts.append((long_char, code3, long_score))

    # 5. 过滤与输出
    valid_shortcuts.sort(key=lambda x: x[2], reverse=True)
    
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
        for char, code, _ in top_n:
            f.write(f"{char}\t{code}\n")
    
    print(f"三简生成完成: {output_path} (数量: {len(top_n)})")

def main():
    parser = argparse.ArgumentParser(description="Wucang5 三简生成脚本")
    parser.add_argument("--gb-only", action="store_true", default=False)
    parser.add_argument("--prefix", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--count", type=int, default=0)
    parser.add_argument("--auto-coverage", type=float, default=0.90)
    args = parser.parse_args()
    generate_shortcut_3(gb_only=args.gb_only, prefix=args.prefix, count=args.count, auto_coverage=args.auto_coverage)

if __name__ == "__main__":
    main()
