"""
一简（One-Code）方案分析与生成工具

本脚本用于对比不同字频表下的一简分配方案，并生成最终的“精英平衡版”建议。

算法核心逻辑：
1. get_one_codes (纯算法):
   - 基于单一语料库（字频表）计算。
   - Tier 1 (StartsWith): 优先寻找以该字母开头的最高频汉字。
   - Tier 2 (Contains): 如果 Top 100 高频字中存在包含该字母的字，且频次超过首码匹配字的 1.8 倍，则允许抢位。

2. get_elite_balanced (精英平衡版):
   - 以“知乎语料”为基底（用户认为最符合现代口语习惯）。
   - 权重分配: Zhihu(4), BLCU(2), Essay(1)。
   - 修正机制：
     a) 共识修正: 如果 Essay 和 BLCU 一致推荐同一个字且得分高于知乎推荐字（需满足倍数阈值），则修正。
     b) 换位逻辑: 若共识字已被占用，则通过交换两个键位的分配来保证唯一性。
     c) 频次修正: 若任一语料中该键位的字加权得分超过知乎字的 1.3 倍，则进行抢位。
     d) 首码保护: 若知乎字是首码匹配而修正字不是，则需 2.5 倍频次差才允许替换。
"""


import sys
from pathlib import Path
from collections import defaultdict

# Add common dir to path for imports
sys.path.append(str(Path(__file__).resolve().parent))
from cangjie_builder import (
    parse_cangjie_dict,
    parse_frequency_file,
    is_han_char,
    REPO_ROOT
)

ORIGINAL_RADICALS = {
    'a': '日', 'b': '月', 'c': '金', 'd': '木', 'e': '水', 'f': '火', 'g': '土',
    'h': '竹', 'i': '戈', 'j': '十', 'k': '大', 'l': '中', 'm': '一', 'n': '弓',
    'o': '人', 'p': '心', 'q': '手', 'r': '口', 's': '尸', 't': '廿', 'u': '山',
    'v': '女', 'w': '田', 'x': '难', 'y': '卜'
}

def get_one_codes(freq_path, char_codes, chars_by_freq, frequencies):
    """纯算法：基于单一字频表，通过阶梯权重机制为每个键位分配一简字。"""
    one_codes = {}
    used_chars = set()
    
    for letter in "abcdefghijklmnopqrstuvwxy":
        orig_char = ORIGINAL_RADICALS.get(letter)
        orig_freq = frequencies.get(orig_char, 0) if orig_char else 0
        
        best_char = orig_char
        current_threshold = orig_freq * 1.5

        # Tier 1: StartsWith — 寻找首码匹配的最高频字
        for char in chars_by_freq:
            if char in used_chars or char == orig_char:
                continue
            char_rank = chars_by_freq.index(char) + 1
            is_start = False
            for code in char_codes[char]:
                if code.startswith(letter):
                    if len(code) <= 3 or char_rank <= 100:
                        is_start = True
                        break
            if is_start:
                char_freq = frequencies.get(char, 0)
                if char_freq > current_threshold:
                    best_char = char
                    current_threshold = char_freq
                break

        # Tier 2: Contains (Top 100) — 允许包含该字母的超高频字跨级抢位
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
                if char_freq > current_threshold * 1.8:
                    best_char = char
                    current_threshold = char_freq
                break
        
        if best_char:
            one_codes[letter] = best_char
            used_chars.add(best_char)
    return one_codes


def get_elite_balanced(char_codes, all_freqs, zhihu_result, essay_result, blcu_result):
    """精英平衡版：以知乎纯算法为基底，多层修正。
    
    修正规则（按优先级）：
    1. Essay+BLCU 共识修正：两者一致推荐且加权得分更高 → 替换（支持换位）。
    2. 频次压倒修正：任一源推荐的字加权得分 > 知乎字的 1.3 倍 → 替换。
    """
    weights = {"Zhihu": 4, "BLCU": 2, "Essay": 1}
    
    char_scores = {}
    for char in char_codes:
        score = sum(all_freqs[src].get(char, 0) * w for src, w in weights.items())
        if score > 0:
            char_scores[char] = score
    
    elite = dict(zhihu_result)
    used_chars = set(elite.values())
    
    # 第一轮：Essay+BLCU 共识修正（支持换位）
    for letter in "abcdefghijklmnopqrstuvwxy":
        essay_char = essay_result.get(letter, "")
        blcu_char = blcu_result.get(letter, "")
        zhihu_char = elite.get(letter, "")
        
        if essay_char == blcu_char and essay_char != zhihu_char and essay_char:
            consensus = essay_char
            consensus_score = char_scores.get(consensus, 0)
            zhihu_score = char_scores.get(zhihu_char, 0)
            
            # 如果知乎字首码匹配当前键位，而共识字不匹配，需要更高门槛
            zhihu_starts = any(code.startswith(letter) for code in char_codes.get(zhihu_char, []))
            consensus_starts = any(code.startswith(letter) for code in char_codes.get(consensus, []))
            threshold = 1.2 if (consensus_starts or not zhihu_starts) else 2.5
            
            if consensus_score > zhihu_score * threshold:
                if consensus not in used_chars:
                    # 直接替换
                    used_chars.discard(zhihu_char)
                    elite[letter] = consensus
                    used_chars.add(consensus)
                else:
                    # 换位：找到占用 consensus 的键位，把当前字换过去
                    other_key = next((k for k, v in elite.items() if v == consensus), None)
                    if other_key:
                        elite[letter] = consensus
                        elite[other_key] = zhihu_char
                        # used_chars 不变（只是交换了两个字的位置）
    
    # 第二轮：频次压倒修正（非共识情况）
    for letter in "abcdefghijklmnopqrstuvwxy":
        zhihu_char = elite.get(letter, "")
        zhihu_score = char_scores.get(zhihu_char, 0)
        
        # 收集 Essay/BLCU 的不同候选
        candidates = set()
        for src_result in [essay_result, blcu_result]:
            c = src_result.get(letter, "")
            if c and c != zhihu_char:
                candidates.add(c)
        
        for cand in sorted(candidates, key=lambda c: char_scores.get(c, 0), reverse=True):
            cand_score = char_scores.get(cand, 0)
            if cand_score > zhihu_score * 1.3 and cand not in used_chars:
                used_chars.discard(zhihu_char)
                elite[letter] = cand
                used_chars.add(cand)
                break
    
    return elite


def main():
    source = REPO_ROOT / "cangjie5/cangjie5.dict.yaml"
    freq_paths = {
        "Essay": REPO_ROOT / "sancang5/essay-zh-hans.txt",
        "Zhihu": REPO_ROOT / "frequency/zhihu_freq.txt",
        "BLCU": REPO_ROOT / "frequency/blcu_freq.txt"
    }

    raw_entries = parse_cangjie_dict(source)
    char_codes = defaultdict(list)
    for entry in raw_entries:
        if is_han_char(entry.text) and not entry.code.startswith('z'):
            char_codes[entry.text].append(entry.code)

    results = {}
    for name, path in freq_paths.items():
        freqs, _ = parse_frequency_file(path)
        chars_by_freq = sorted(char_codes.keys(), key=lambda c: freqs.get(c, 0), reverse=True)
        results[name] = get_one_codes(path, char_codes, chars_by_freq, freqs)

    # Load current sicang5_1.txt
    current_codes = {}
    current_path = REPO_ROOT / "sicang5/sicang5_1.txt"
    if current_path.exists():
        with open(current_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split("\t")
                if len(parts) == 2:
                    current_codes[parts[1]] = parts[0]

    # Load 简体仓颉.txt
    jiancang_codes = {}
    jiancang_path = REPO_ROOT / "_tmp_jiancang/简体仓颉.txt"
    if jiancang_path.exists():
        with open(jiancang_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                parts = line.split("\t")
                if len(parts) == 2:
                    char, code = parts[0], parts[1]
                    if len(code) == 1:
                        # 仅保留第一次出现的（通常是高频字）
                        if code not in jiancang_codes:
                            jiancang_codes[code] = char

    # 加载三份字频表的原始频次数据，供精英平衡版算法使用
    all_freqs = {}
    for name, path in freq_paths.items():
        freqs, _ = parse_frequency_file(path)
        all_freqs[name] = freqs

    # 计算精英平衡版：以知乎为基底，Essay/BLCU 共识修正
    elite_balanced = get_elite_balanced(
        char_codes, all_freqs,
        zhihu_result=results["Zhihu"],
        essay_result=results["Essay"],
        blcu_result=results["BLCU"]
    )

    # Write Markdown table
    output_path = REPO_ROOT / "sicang5/one_code_comparison.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 一简方案分配对比表\n\n")
        f.write("本表对比了：\n")
        f.write("1. **纯算法**：基于三份字频表各自独立计算。\n")
        f.write("2. **当前正式版**：当前使用的校准方案。\n")
        f.write("3. **简体仓颉**：第三方方案参考。\n")
        f.write("4. **精英平衡版**：以知乎纯算法为基底，当 Essay 和 BLCU 一致推荐")
        f.write("另一个更高频字时自动修正。\n\n")
        f.write("| 键位 | Essay (纯算法) | Zhihu (纯算法) | BLCU (纯算法) | 当前正式版 | 简体仓颉 | **精英平衡版** |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for letter in "abcdefghijklmnopqrstuvwxy":
            e = results["Essay"].get(letter, "")
            z = results["Zhihu"].get(letter, "")
            b = results["BLCU"].get(letter, "")
            curr = current_codes.get(letter, "")
            jc = jiancang_codes.get(letter, "")
            elite = elite_balanced.get(letter, "")
            f.write(f"| {letter} | {e} | {z} | {b} | {curr} | {jc} | **{elite}** |\n")
    print(f"对比结果已保存至: {output_path}")

if __name__ == "__main__":
    main()
