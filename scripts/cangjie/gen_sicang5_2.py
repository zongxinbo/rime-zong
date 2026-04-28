#!/usr/bin/env python3
"""
Sicang5 二简方案设计脚本
1. 提取规则：单字首尾码 (Aa + Az)。
2. 竞争机制：允许长码字与“原主字”(全码=2)竞争首选位。若长码字频次 > 原主频次 * 1.5，则生成简码。
3. 输出限制：仅输出长码字作为简码，原主字依赖全量词库自然存在。
"""

import sys
from pathlib import Path
from collections import defaultdict

# 导入通用工具
sys.path.append(str(Path(__file__).resolve().parent))
from cangjie_builder import (
    parse_cangjie_dict,
    parse_frequency_file,
    is_han_char,
    REPO_ROOT
)

def main():
    source_dict = REPO_ROOT / "cangjie5/cangjie5.dict.yaml"
    freq_file = REPO_ROOT / "sancang5/essay-zh-hans.txt"
    weights = {"Dialogue": 6, "Subtlex": 5, "Zhihu": 4, "BLCU": 2, "Essay": 1}
    output_path = REPO_ROOT / "sicang5/sicang5_2.txt"

    # 1. 排除名单 (z 和 1)
    excluded_chars = set()
    for f_name in ["sicang5_z.txt", "sicang5_1.txt"]:
        p = REPO_ROOT / "sicang5" / f_name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 1 and parts[0] and not parts[0].startswith("#"):
                        excluded_chars.add(parts[0])

    # 2. 计算加权得分
    freq_paths = {
        "Dialogue": REPO_ROOT / "frequency/char/dialogue_char_freq.txt",
        "Subtlex": REPO_ROOT / "frequency/char/subtlex_char_freq.txt",
        "Zhihu": REPO_ROOT / "frequency/char/zhihu_char_freq.txt",
        "BLCU": REPO_ROOT / "frequency/char/blcu_char_freq.txt",
        "Essay": REPO_ROOT / "sancang5/essay-zh-hans.txt"
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
    
    # 3. 按 projected_code 分组，记录所有候选
    # code2: { "orig": (char, score), "long": [(char, score), ...] }
    candidates_by_code = defaultdict(lambda: {"orig": None, "long": []})
    
    for char, full_code in char_codes.items():
        score = char_scores.get(char, 0)
        if score <= 0: continue
        
        if len(full_code) == 2:
            # 记录/更新原主最高分
            curr_orig = candidates_by_code[full_code]["orig"]
            if not curr_orig or score > curr_orig[1]:
                candidates_by_code[full_code]["orig"] = (char, score)
        elif len(full_code) > 2:
            code2 = full_code[0] + full_code[-1]
            candidates_by_code[code2]["long"].append((char, score))

    # 4. 竞争判定
    valid_shortcuts = []
    for code2, data in candidates_by_code.items():
        if not data["long"]: continue # 没有长码字来竞争
        
        # 找出最强的长码字
        best_long = max(data["long"], key=lambda x: x[1])
        long_char, long_score = best_long
        
        # 门槛判定
        is_empty = False
        threshold = 0
        if data["orig"]:
            threshold = data["orig"][1] * 1.5 # 抢占原主首选位需 1.5 倍
        else:
            is_empty = True
            
        if long_score > threshold:
            valid_shortcuts.append((long_char, code2, long_score, is_empty))

    # 5. 排序并取 Top 150
    # 路线 B (混合双打)：达到门槛后，统一按长码字的绝对频次(score)竞争 Top 名额
    valid_shortcuts.sort(key=lambda x: x[2], reverse=True)
    top_n = valid_shortcuts[:150]
    top_n.sort(key=lambda x: x[1])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 二简\n")
        for char, code, _, _ in top_n:
            f.write(f"{char}\t{code}\n")
    
    print(f"二简设计稿已生成(优先绝对空位+合理竞争): {output_path} (数量: {len(top_n)})")

if __name__ == "__main__":
    main()
