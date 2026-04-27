import sys
import argparse
from pathlib import Path
from collections import defaultdict
import datetime as _dt
from cangjie_builder import (
    parse_cangjie_dict,
    parse_frequency_file,
    is_han_char,
    REPO_ROOT
)

def get_two_code(full_code):
    """提取二简码：首码 + 末码"""
    if len(full_code) < 2: return full_code
    return full_code[0] + full_code[-1]

def get_three_code(full_code):
    """提取三简码：首码 + 次码 + 末码"""
    if len(full_code) < 3: return full_code
    return full_code[0] + full_code[1] + full_code[-1]

def project_code(full_code, max_len):
    """根据最大长度缩减全码"""
    if len(full_code) <= max_len: return full_code
    return full_code[:max_len-1] + full_code[-1]

def run_sicang5_generator():
    parser = argparse.ArgumentParser(description="生成 4码仓颉 (sicang5) 方案")
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "cangjie5/cangjie5.dict.yaml")
    parser.add_argument("--frequency-file", type=Path, default=REPO_ROOT / "sancang5/essay-zh-hans.txt")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "sicang5")
    args = parser.parse_args()

    # 1. 加载数据
    raw_entries = parse_cangjie_dict(args.source)
    frequencies, _ = parse_frequency_file(args.frequency_file)
    
    # 过滤非汉字和 z 开头的符号
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

    # 3. 一简 (a-y) - 全局最优分配算法 (Global Greedy Optimization)
    # 目的：将最高频的 25 个字根据形状特征最优化地分配到 25 个按键上
    one_codes = {}
    
    # 建立所有可能的 (字, 键) 竞选对
    candidates = []
    # 只考虑排名前 500 的字作为一简候选
    top_500 = chars_by_freq[:500]
    
    for char in top_500:
        char_rank = chars_by_freq.index(char) + 1
        char_freq = frequencies.get(char, 0)
        
        # 获取该字的所有仓颉码
        for code in char_codes[char]:
            letters_in_code = set(code)
            for letter in letters_in_code:
                if letter not in "abcdefghijklmnopqrstuvwxy":
                    continue
                
                # 轻盈度规则：非 Top 50 候选全码不能超过 3 码
                if len(code) > 3 and char_rank > 50:
                    continue
                
                # 计算得分逻辑 (Greedy Score)
                # 权重：原字根(1.5) > 首码匹配(1.2) > 包含匹配(1.0)
                is_radical = (char == ORIGINAL_RADICALS.get(letter))
                is_start = code.startswith(letter)
                
                weight = 1.0
                if is_radical:
                    weight = 1.5
                elif is_start:
                    weight = 1.2
                else:
                    # 包含规则仅限 Top 100 参与竞争
                    if char_rank > 100:
                        continue
                    weight = 1.0
                
                score = char_freq * weight
                candidates.append({
                    "char": char,
                    "letter": letter,
                    "score": score
                })
    
    # 按得分贪心分配
    candidates.sort(key=lambda x: x["score"], reverse=True)
    used_chars = set()
    used_letters = set()
    
    for cand in candidates:
        if cand["char"] not in used_chars and cand["letter"] not in used_letters:
            one_codes[cand["letter"]] = cand["char"]
            used_chars.add(cand["char"])
            used_letters.add(cand["letter"])
            
    # 兜底：确保 25 个键都有字 (补回原字根)
    for letter in "abcdefghijklmnopqrstuvwxy":
        if letter not in used_letters:
            orig_char = ORIGINAL_RADICALS.get(letter)
            if orig_char and orig_char not in used_chars:
                one_codes[letter] = orig_char
                used_chars.add(orig_char)
                used_letters.add(letter)

    # 4. 二简 (首码 + 末码)
    two_codes = {}
    top_1000 = chars_by_freq[:1000]
    for char in top_1000:
        for code in char_codes[char]:
            two_code = get_two_code(code)
            sicang_full = project_code(code, 4)
            if len(two_code) == 2 and two_code != sicang_full and two_code not in two_codes:
                two_codes[two_code] = char

    # 5. 三简 (首码 + 次码 + 末码)
    three_codes = {}
    for char in top_1000:
        for code in char_codes[char]:
            three_code = get_three_code(code)
            sicang_full = project_code(code, 4)
            if len(three_code) == 3 and three_code != sicang_full and three_code not in three_codes:
                three_codes[three_code] = char

    # 6. 生成全码字典 (sicang5)
    full_entries = []
    for char in chars_by_freq:
        for code in char_codes[char]:
            full_entries.append((char, project_code(code, 4), frequencies.get(char, 0)))

    # 输出各个阶段的文件
    def write_txt(filename, data_dict, header_title):
        path = args.output_dir / filename
        with path.open("w", encoding="utf-8") as f:
            f.write(f"# {header_title}\n")
            for k, v in sorted(data_dict.items()):
                f.write(f"{v}\t{k}\n")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_txt("sicang5_z.txt", z_codes, "原字根")
    write_txt("sicang5_1.txt", one_codes, "一简")
    write_txt("sicang5_2.txt", two_codes, "二简")
    write_txt("sicang5_3.txt", three_codes, "三简")

    # 生成最终 Rime 字典
    final_dict_path = args.output_dir / "sicang5.dict.yaml"
    header = f"""#
# 极速单字四码仓颉（sicang5）
# 由 scripts/gen_sicang5.py 自动生成
# 包含：原字根z引导、一简、二简、三简、全码
---
name: sicang5
version: '{_dt.date.today().isoformat()}'
sort: by_weight
...
"""
    lines = []
    written_entries = set()
    def add_entry(text, code):
        if (text, code) not in written_entries:
            lines.append(f"{text}\t{code}")
            written_entries.add((text, code))

    for k, v in sorted(z_codes.items()): add_entry(v, k)
    for k, v in sorted(one_codes.items()): add_entry(v, k)
    for k, v in sorted(two_codes.items()): add_entry(v, k)
    for k, v in sorted(three_codes.items()): add_entry(v, k)
    for text, code, _ in full_entries: add_entry(text, code)

    with final_dict_path.open("w", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write("\n".join(lines) + "\n")

    print(f"成功生成字典: {final_dict_path}")
    print(f"统计: z={len(z_codes)} 1={len(one_codes)} 2={len(two_codes)} 3={len(three_codes)} 4={len(full_entries)}")

if __name__ == "__main__":
    run_sicang5_generator()
