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
    if len(full_code) < 2: return full_code
    return full_code[0] + full_code[-1]

def get_three_code(full_code):
    if len(full_code) < 3: return full_code
    return full_code[0] + full_code[1] + full_code[-1]

def project_code(full_code, max_len):
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
    
    filtered_entries = []
    for entry in raw_entries:
        if is_han_char(entry.text) and not entry.code.startswith('z'):
            filtered_entries.append((entry.text, entry.code))

    char_codes = defaultdict(list)
    for text, code in filtered_entries:
        char_codes[text].append(code)

    chars_by_freq = sorted(char_codes.keys(), key=lambda c: frequencies.get(c, 0), reverse=True)

    # 2. 原字根
    ORIGINAL_RADICALS = {
        'a': '日', 'b': '月', 'c': '金', 'd': '木', 'e': '水', 'f': '火', 'g': '土',
        'h': '竹', 'i': '戈', 'j': '十', 'k': '大', 'l': '中', 'm': '一', 'n': '弓',
        'o': '人', 'p': '心', 'q': '手', 'r': '口', 's': '尸', 't': '廿', 'u': '山',
        'v': '女', 'w': '田', 'x': '难', 'y': '卜'
    }
    z_codes = {}
    for letter, char in ORIGINAL_RADICALS.items():
        z_codes[letter + "z"] = char

    # 3. 一简分配逻辑：阶梯权重算法 + 人工校准
    # 用户指出这套算法价值极高，故保留算法骨架，并通过校准字典进行最终微调。
    one_codes = {}
    used_chars = set()
    
    # 算法计算阶段
    for letter in "abcdefghijklmnopqrstuvwxy":
        orig_char = ORIGINAL_RADICALS.get(letter)
        orig_freq = frequencies.get(orig_char, 0) if orig_char else 0
        
        best_char = orig_char
        current_threshold = orig_freq * 1.5

        # 第一级：寻找以该字母【开头】的候选字 (1.5倍频保护)
        for char in chars_by_freq:
            if char in used_chars or char == orig_char:
                continue
            
            char_rank = chars_by_freq.index(char) + 1
            is_start = False
            for code in char_codes[char]:
                if code.startswith(letter):
                    # 长度限制：非 Top 100 的字全码不能超过 3 码
                    if len(code) <= 3 or char_rank <= 100:
                        is_start = True
                        break
            if is_start:
                char_freq = frequencies.get(char, 0)
                if char_freq > current_threshold:
                    best_char = char
                    current_threshold = char_freq
                break # 找到首码匹配最高的即可

        # 第二级：跨级抢位 (Contains 规则，仅限 Top 100，且需 3 倍频次)
        for char in chars_by_freq:
            if char in used_chars or char == orig_char or char == best_char:
                continue
            char_rank = chars_by_freq.index(char) + 1
            if char_rank > 100: break
            
            is_contained = False
            for code in char_codes[char]:
                if letter in code:
                    if len(code) <= 3 or char_rank <= 100:
                        is_contained = True
                        break
            if is_contained:
                char_freq = frequencies.get(char, 0)
                if char_freq > current_threshold * 3.0:
                    best_char = char
                    current_threshold = char_freq
                break # 找到包含匹配最高的即可
        
        if best_char:
            one_codes[letter] = best_char
            used_chars.add(best_char)

    # 人工直觉校准阶段 (Human Calibration)
    # 算法有时无法兼顾人类主观认知，因此保留这一套校准层，强制覆盖算法的盲点。
    # 这也是现代输入法最科学的构建方式：算法铺底 + 人类校准。
    HUMAN_CALIBRATION = {
        'a': '是', 'b': '用', 'c': '小', 'd': '和', 
        'h': '的', 'i': '我', 'k': '有', 'r': '说', 
        's': '为', 'x': '已'
    }
    
    for letter, cal_char in HUMAN_CALIBRATION.items():
        # 如果该字已经被其他字母占用，先释放它
        for k, v in list(one_codes.items()):
            if v == cal_char and k != letter:
                # 把那个位置还给它的原字根
                one_codes[k] = ORIGINAL_RADICALS.get(k)
        one_codes[letter] = cal_char

    # 4. 二三简 (Top 1000)
    two_codes = {}
    top_1000 = chars_by_freq[:1000]
    for char in top_1000:
        for code in char_codes[char]:
            two_code = get_two_code(code)
            sicang_full = project_code(code, 4)
            if len(two_code) == 2 and two_code != sicang_full and two_code not in two_codes:
                two_codes[two_code] = char

    # 5. 三简 (Top 1000)
    three_codes = {}
    for char in top_1000:
        for code in char_codes[char]:
            three_code = get_three_code(code)
            sicang_full = project_code(code, 4)
            if len(three_code) == 3 and three_code != sicang_full and three_code not in three_codes:
                three_codes[three_code] = char

    # 6. 全码 (Sicang5: 提取四码)
    full_entries = []
    for char in chars_by_freq:
        for code in char_codes[char]:
            full_entries.append((char, project_code(code, 4)))

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

    # 7. 写入最终字典文件 (sicang5.dict.yaml)
    # 合并原字根、一、二、三、全码，并依靠物理写入顺序保证简码绝对优先
    final_dict_path = args.output_dir / "sicang5.dict.yaml"
    header = f"""#
# 极速单字四码仓颉（sicang5）
# 由 scripts/gen_sicang5.py 自动生成
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
    for text, code in full_entries: add_entry(text, code)

    with final_dict_path.open("w", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write("\n".join(lines) + "\n")

if __name__ == "__main__":
    run_sicang5_generator()
