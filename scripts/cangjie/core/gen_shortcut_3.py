#!/usr/bin/env python3
"""
Wucang5 三简方案生成脚本

规则：
  1. 取码：full_code[:3]（顺位前缀）
  2. 资格：仅 GB2312 汉字
  3. 保护：3 码槽位有 GB2312 原主字（全码恰好=3）→ 禁止抢占
  4. 空槽直接占据：最高频的 GB2312 长码字直接获得简码
  5. 排他：已在 S1/Z/S2 排除名单中的字不参与
"""

import sys
from pathlib import Path
from collections import defaultdict

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


def generate_shortcut_3():
    source_dict = REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml"
    output_path = REPO_ROOT / "scripts/cangjie/prototypes/three_code.txt"

    # 加权得分
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

    # 1. 排除名单 (z 码 + 一简 + 二简)
    excluded_chars = set()
    for f_name in ["z_code.txt", "one_code.txt", "two_code.txt"]:
        p = REPO_ROOT / "scripts/cangjie/prototypes" / f_name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 1 and parts[0] and not parts[0].startswith("#"):
                        excluded_chars.add(parts[0])

    # 2. 加载仓颉码表
    raw_entries = parse_cangjie_dict(source_dict)
    char_codes = {}
    for e in raw_entries:
        if not is_han_char(e.text) or e.code.startswith('z') or e.code.startswith('x'):
            continue
        if e.text in excluded_chars:
            continue
        if e.text not in char_codes or len(e.code) < len(char_codes[e.text]):
            char_codes[e.text] = e.code

    # 3. 找出所有 GB2312 原主字（全码恰好=3）
    gb_owners_3 = set()
    for char, code in char_codes.items():
        if len(code) == 3 and is_gb2312(char):
            gb_owners_3.add(code)

    # 4. 为每个空槽找最高频的 GB2312 长码字
    slot_candidates = defaultdict(list)
    for char, code in char_codes.items():
        if len(code) <= 3:
            continue
        if not is_gb2312(char):
            continue
        score = char_scores.get(char, 0)
        if score <= 0:
            continue
        code3 = code[:3]
        if code3 in gb_owners_3:
            continue  # GB2312 原主保护
        slot_candidates[code3].append((score, char))

    # 5. 每个空槽选出最高频的字
    shortcuts = []
    for code3, candidates in slot_candidates.items():
        candidates.sort(key=lambda x: -x[0])
        best_score, best_char = candidates[0]
        shortcuts.append((best_char, code3, best_score))

    shortcuts.sort(key=lambda x: x[1])

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 三简\n")
        for char, code, _ in shortcuts:
            f.write(f"{char}\t{code}\n")

    print(f"三简生成完成: {output_path} (数量: {len(shortcuts)})")


def main():
    generate_shortcut_3()


if __name__ == "__main__":
    main()
