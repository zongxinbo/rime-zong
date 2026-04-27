#!/usr/bin/env python3
"""生成带有一简、二简、三简提速的四码仓颉（sicang5）单字码表。"""

import argparse
import sys
import datetime as _dt
from collections import defaultdict
from pathlib import Path

from cangjie_builder import (
    REPO_ROOT,
    parse_cangjie_dict,
    parse_frequency_file,
    is_han_char,
    project_code,
)

def get_two_code(code: str) -> str:
    """提取首末码作为二简"""
    if len(code) >= 2:
        return code[0] + code[-1]
    return ""

def get_three_code(code: str) -> str:
    """提取首次末码作为三简（即三码仓颉规则）"""
    if len(code) >= 3:
        return code[:2] + code[-1]
    return ""

def main():
    parser = argparse.ArgumentParser(description="生成带简码提速的四码仓颉字典。")
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "cangjie5/cangjie5.dict.yaml", help="源仓颉五代码表")
    parser.add_argument("--frequency-file", type=Path, default=REPO_ROOT / "sancang5/essay-zh-hans.txt", help="词频文件")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "sicang5", help="输出目录")
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"找不到源文件：{args.source}", file=sys.stderr)
        return 2

    # 1. 加载字典条目和词频
    raw_entries = parse_cangjie_dict(args.source)
    frequencies, _ = parse_frequency_file(args.frequency_file)

    # 过滤规则：必须是纯汉字，且不能以 'z' 开头（排除原有的标点符号等）
    filtered_entries = []
    for entry in raw_entries:
        if is_han_char(entry.text) and not entry.code.startswith('z'):
            filtered_entries.append((entry.text, entry.code))

    char_codes = defaultdict(list)
    for text, code in filtered_entries:
        char_codes[text].append(code)

    # 将字符按照词频从高到低排序
    chars_by_freq = sorted(char_codes.keys(), key=lambda c: frequencies.get(c, 0), reverse=True)

    # 2. 提取原字根并使用 z 作为后缀兜底 (az-yz)
    ORIGINAL_RADICALS = {
        'a': '日', 'b': '月', 'c': '金', 'd': '木', 'e': '水', 'f': '火', 'g': '土',
        'h': '竹', 'i': '戈', 'j': '十', 'k': '大', 'l': '中', 'm': '一', 'n': '弓',
        'o': '人', 'p': '心', 'q': '手', 'r': '口', 's': '尸', 't': '廿', 'u': '山',
        'v': '女', 'w': '田', 'y': '卜'
    }
    z_codes = {}
    for letter, char in ORIGINAL_RADICALS.items():
        z_codes[letter + "z"] = char

    # 3. 一简 (a-y) - 首码限制与 3倍频保护机制
    one_codes = {}
    used_chars = set()
    for letter in "abcdefghijklmnopqrstuvwxy":
        orig_char = ORIGINAL_RADICALS.get(letter)
        orig_freq = frequencies.get(orig_char, 0) if orig_char else 0
        best_char = orig_char

        # 1-code 竞争逻辑：原字根 > 首码匹配 > 包含该码
        # 优先级权重：首码匹配需要是原字根的 1.5 倍频；包含该码需要是当前最优(首码)的 3 倍频
        best_char = orig_char
        current_threshold = orig_freq * 1.5
        
        # 第一轮：寻找以该字母【开头】的候选字 (1.5倍频保护)
        for char in chars_by_freq:
            if char in used_chars or char == orig_char:
                continue
            
            char_rank = chars_by_freq.index(char) + 1
            is_start = False
            for code in char_codes[char]:
                if code.startswith(letter):
                    # 长度限制：非 Top 50 的字全码不能超过 3 码
                    if len(code) <= 3 or char_rank <= 50:
                        is_start = True
                        break
            
            if is_start:
                char_freq = frequencies.get(char, 0)
                if char_freq > current_threshold:
                    best_char = char
                    current_threshold = char_freq
                # 找到该字母开头最高频的即可（因为 chars_by_freq 已排序）
                break
        
        # 第二轮：如果用户允许，寻找【包含】该字母但不是开头的超高频字 (3倍频抢占)
        # 只有当包含该字母的字频次 远大于 当前确定的 best_char 时才允许抢占
        for char in chars_by_freq:
            if char in used_chars or char == orig_char or char == best_char:
                continue
                
            char_rank = chars_by_freq.index(char) + 1
            if char_rank > 100: # 包含规则只允许 Top 100 的超级高频字竞选
                break
                
            is_contained = False
            for code in char_codes[char]:
                if letter in code: # 包含即可
                    if len(code) <= 3 or char_rank <= 50:
                        is_contained = True
                        break
            
            if is_contained:
                char_freq = frequencies.get(char, 0)
                # 必须是当前最优候选字频次的 3 倍以上才能“跨级抢位”
                if char_freq > current_threshold * 3:
                    best_char = char
                    current_threshold = char_freq
                # 找到最高的即可
                break
        
        if best_char:
            one_codes[letter] = best_char
            used_chars.add(best_char)

    # 4. 二简 (首码 + 末码)
    two_codes = {}
    top_3000 = chars_by_freq[:3000] # 仅限字频前 3000 名的高频字竞选二简
    for char in top_3000:
        for code in char_codes[char]:
            two_code = get_two_code(code)
            sicang_full = project_code(code, 4)
            # 如果提取出的二简和它最终的四码全码完全一样，则跳过（避免冗余）
            if len(two_code) == 2 and two_code != sicang_full and two_code not in two_codes:
                two_codes[two_code] = char

    # 5. 三简 (首码 + 次码 + 末码) - 仅限字频前 1000 名
    three_codes = {}
    top_1000 = chars_by_freq[:1000]
    for char in top_1000:
        for code in char_codes[char]:
            three_code = get_three_code(code)
            sicang_full = project_code(code, 4)
            # 如果提取出的三简和全码完全一样，则跳过
            if len(three_code) == 3 and three_code != sicang_full and three_code not in three_codes:
                three_codes[three_code] = char

    # 6. 四码全码 (Sicang5规则: 首 + 次 + 三 + 末)
    full_entries = []
    for text, code in filtered_entries:
        sicang_code = project_code(code, 4)
        full_entries.append((text, sicang_code, frequencies.get(text, 0)))

    # 将全码按编码字母顺序升序排序，然后按字频降序排列
    full_entries.sort(key=lambda x: (x[1], -x[2]))

    # 输出为单独的 txt 文本文件
    args.output_dir.mkdir(exist_ok=True)
    
    def write_txt(filename, data_dict, title):
        with open(args.output_dir / filename, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n")
            for k, v in sorted(data_dict.items()):
                f.write(f"{v}\t{k}\n")

    write_txt("sicang5_z.txt", z_codes, "原字根")
    write_txt("sicang5_1.txt", one_codes, "一简")
    write_txt("sicang5_2.txt", two_codes, "二简")
    write_txt("sicang5_3.txt", three_codes, "三简")

    # 7. 生成最终的 Rime dict 字典文件
    final_dict_path = args.output_dir / "sicang5.dict.yaml"
    version = _dt.date.today().isoformat()
    header = f"""# encoding: utf-8
#
# 极速单字四码仓颉（sicang5）
# 由 scripts/gen_sicang5.py 自动生成
# 包含：原字母z引导、一简(同首码)、二简(首末)、三简(首次末, 前3000字)、全码(一二三末)
# 排序：自然排序 (Natural Sorting)，依靠物理写入顺序保证简码绝对优先。
#
---
name: sicang5
version: '{version}'
sort: original
max_phrase_length: 1
...
"""
    lines = []
    written_entries = set()

    def add_entry(text, code):
        item = (text, code)
        if item not in written_entries:
            lines.append(f"{text}\t{code}")
            written_entries.add(item)

    for k, v in sorted(z_codes.items()):
        add_entry(v, k)
    for k, v in sorted(one_codes.items()):
        add_entry(v, k)
    for k, v in sorted(two_codes.items()):
        add_entry(v, k)
    for k, v in sorted(three_codes.items()):
        add_entry(v, k)
    for text, code, _ in full_entries:
        add_entry(text, code)

    with open(final_dict_path, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write("\n".join(lines) + "\n")

    print(f"完成: 生成了 {final_dict_path}")
    print(f"统计: z兜底={len(z_codes)} 一简={len(one_codes)} 二简={len(two_codes)} 三简={len(three_codes)} 全码={len(full_entries)}")

if __name__ == "__main__":
    sys.exit(main())
