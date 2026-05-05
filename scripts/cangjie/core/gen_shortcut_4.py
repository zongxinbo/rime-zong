#!/usr/bin/env python3
"""
Wucang5 强制四简方案生成脚本

规则：
  1. 对象：全码=5 且属于 GB2312 且未在 S1/Z/S2/S3 中获得分配的字
  2. 取码：full_code[:4]
  3. 无竞争保护：允许物理重码
"""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.cangjie_builder import (
    parse_cangjie_dict,
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


def generate_shortcut_4():
    source_dict = REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml"
    output_path = REPO_ROOT / "scripts/cangjie/prototypes/four_code.txt"

    # 1. 排除名单 (z 码 + 一简 + 二简 + 三简)
    excluded_chars = set()
    for f_name in ["z_code.txt", "one_code.txt", "two_code.txt", "three_code.txt"]:
        p = REPO_ROOT / "scripts/cangjie/prototypes" / f_name
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 1 and parts[0] and not parts[0].startswith("#"):
                        excluded_chars.add(parts[0])

    # 2. 加载仓颉码表
    raw_entries = parse_cangjie_dict(source_dict)
    # 对每个字，收集所有全码（一个字可能有多个 5 码编码）
    char_five_codes = defaultdict(list)
    for e in raw_entries:
        if not is_han_char(e.text) or e.code.startswith('z') or e.code.startswith('x'):
            continue
        if e.text in excluded_chars:
            continue
        if not is_gb2312(e.text):
            continue
        if len(e.code) == 5:
            char_five_codes[e.text].append(e.code)

    # 3. 为每个 5 码字生成 4 码简码
    shortcuts = []
    seen = set()  # 避免同一个字输出多次
    for char, codes in char_five_codes.items():
        if char in seen:
            continue
        seen.add(char)
        for code in codes:
            shortcuts.append((char, code[:4]))

    shortcuts.sort(key=lambda x: x[1])  # 按编码排序

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 四简（强制截断）\n")
        for char, code in shortcuts:
            f.write(f"{char}\t{code}\n")

    print(f"四简生成完成: {output_path} (数量: {len(shortcuts)})")


def main():
    generate_shortcut_4()


if __name__ == "__main__":
    main()
