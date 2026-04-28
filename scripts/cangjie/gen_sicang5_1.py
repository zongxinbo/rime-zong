"""
Sicang5 一简（One-Code）方案设计脚本

本脚本用于对比不同字频表下的一简分配方案，并生成建议稿 (sicang5_1.txt)。

算法核心逻辑：
1. get_one_codes (纯算法):
   - 基于单一语料库（字频表）计算。
   - Tier 1 (StartsWith): 优先寻找以该字母开头的最高频汉字。
   - Tier 2 (Contains): 如果 Top 100 高频字中存在包含该字母的字，且频次超过首码匹配字的 1.8 倍，则允许抢位。

2. get_final_version (最终版):
   - 以“Dialogue”（口语语料）为基底，确保口语常用字绝对优先。
   - 权重分配: Dialogue(6), Subtlex(5), Zhihu(4), BLCU(2), Essay(1)。
     （最终列加权时口语字频权重第一）
   - 修正机制：
     a) 加权修正: 若任一其他语料推荐的字，其加权总分超过基底字的倍数阈值，则修正。
     b) 首码保护: 若基底字是首码匹配而修正字不是，则需 2.5 倍频次差才允许替换；否则为 1.2 倍。
     c) 换位逻辑: 若高分字已被占用，则通过交换两个键位的分配来保证唯一性。
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


def get_final_version(char_codes, all_freqs, results):
    """最终版：以口语语料（Dialogue）为基底，利用多源加权总分进行修正。"""
    
    weights = {
        "Dialogue": 6,
        "Subtlex": 5,
        "Zhihu": 4,
        "BLCU": 2,
        "Essay": 1
    }
    
    char_scores = {}
    for char in char_codes:
        score = sum(all_freqs[src].get(char, 0) * w for src, w in weights.items() if src in all_freqs)
        if score > 0:
            char_scores[char] = score
    
    # 强制保护/优先分配 (习惯与用户指定优先)
    # 用户最终提议方案：
    # a:是, d:来, t:着, g:去, k:在, f:你, h:的, i:我, m:一, r:只, v:好, x:以
    protected_map = {
        'a': '是', 'd': '来', 't': '着', 'g': '去', 
        'k': '在', 'f': '你', 'h': '的', 'i': '我', 
        'm': '一', 'r': '只', 'v': '好', 'x': '以'
    }
    
    # 默认以最高权重的纯口语语料结果为基底
    elite = dict(results["Dialogue"])
    
    # 应用保护策略
    for k, v in protected_map.items():
        if v in char_codes:
            # 彻底清理：如果该保护字已经在别的位子，先清除
            old_k = next((key for key, val in elite.items() if val == v), None)
            if old_k: elite.pop(old_k)
            # 如果该位子已经有别的字，先清理
            old_val = elite.get(k)
            if old_val and old_val != v:
                pass # elite[k] 会被覆盖，但需确保 old_val 不会再次出现
            elite[k] = v

    used_chars = set(elite.values())
    
    # 综合得分修正
    for letter in "abcdefghijklmnopqrstuvwxy":
        # 保护位不参与被抢占
        if letter in protected_map: continue
        
        base_char = elite.get(letter, "")
        base_score = char_scores.get(base_char, 0)
        
        candidates = set()
        for src, res in results.items():
            c = res.get(letter, "")
            # 过滤掉一些不适合做一简的语气词（可选）
            if c == '哈' and letter == 'r': continue 
            if c and c != base_char and c not in protected_map.values():
                candidates.add(c)
                
        for cand in sorted(candidates, key=lambda c: char_scores.get(c, 0), reverse=True):
            cand_score = char_scores.get(cand, 0)
            
            base_starts = any(code.startswith(letter) for code in char_codes.get(base_char, []))
            cand_starts = any(code.startswith(letter) for code in char_codes.get(cand, []))
            
            threshold = 1.2 if (cand_starts or not base_starts) else 2.5
            
            if cand_score > base_score * threshold:
                if cand not in used_chars:
                    used_chars.discard(base_char)
                    elite[letter] = cand
                    used_chars.add(cand)
                    break
                else:
                    # 换位逻辑：增加有效性检查
                    other_key = next((k for k, v in elite.items() if v == cand), None)
                    if other_key and other_key not in protected_map:
                        # 检查 base_char 是否能放在 other_key 
                        base_valid_for_other = False
                        for code in char_codes.get(base_char, []):
                            if other_key in code: # Tier 2 逻辑
                                base_valid_for_other = True
                                break
                        
                        if base_valid_for_other:
                            elite[letter] = cand
                            elite[other_key] = base_char
                            break
    
    return elite


def main():
    source = REPO_ROOT / "cangjie5/cangjie5.dict.yaml"
    freq_paths = {
        "Dialogue": REPO_ROOT / "frequency/char/dialogue_char_freq.txt",
        "Subtlex": REPO_ROOT / "frequency/char/subtlex_char_freq.txt",
        "Zhihu": REPO_ROOT / "frequency/char/zhihu_char_freq.txt",
        "BLCU": REPO_ROOT / "frequency/char/blcu_char_freq.txt",
        "Essay": REPO_ROOT / "sancang5/essay-zh-hans.txt"
    }

    raw_entries = parse_cangjie_dict(source)
    char_codes = defaultdict(list)
    for entry in raw_entries:
        if is_han_char(entry.text) and not entry.code.startswith('z'):
            char_codes[entry.text].append(entry.code)

    results = {}
    all_freqs = {}
    for name, path in freq_paths.items():
        if path.exists():
            freqs, _ = parse_frequency_file(path)
            all_freqs[name] = freqs
            chars_by_freq = sorted(char_codes.keys(), key=lambda c: freqs.get(c, 0), reverse=True)
            results[name] = get_one_codes(path, char_codes, chars_by_freq, freqs)
        else:
            print(f"Warning: {path} not found.")

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

    if "Dialogue" in results:
        final_version = get_final_version(char_codes, all_freqs, results)
    else:
        final_version = {}
        print("Error: Required Dialogue frequencies missing.")

    output_path = REPO_ROOT / "sicang5/one_code_comparison.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# 一简方案分配对比表\n\n")
        f.write("本表对比了：\n")
        f.write("1. **纯算法**：基于五份字频表各自独立计算。\n")
        f.write("2. **当前正式版**：当前使用的校准方案。\n")
        f.write("3. **最终版**：以最高权重的口语语料(Dialogue)为基底，当其他语料出现综合加权更高分的字时触发自动修正，支持换位策略。\n\n")

        f.write("| 键位 | Dialogue (纯算法) | Subtlex (纯算法) | Zhihu (纯算法) | BLCU (纯算法) | Essay (纯算法) | 当前正式版 | **最终版** |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for letter in "abcdefghijklmnopqrstuvwxy":
            d = results.get("Dialogue", {}).get(letter, "")
            s = results.get("Subtlex", {}).get(letter, "")
            z = results.get("Zhihu", {}).get(letter, "")
            b = results.get("BLCU", {}).get(letter, "")
            e = results.get("Essay", {}).get(letter, "")
            curr = current_codes.get(letter, "")
            elite = final_version.get(letter, "")
            f.write(f"| {letter} | {d} | {s} | {z} | {b} | {e} | {curr} | **{elite}** |\n")
    print(f"对比结果已保存至: {output_path}")

    # 同时更新实际的一简方案文件
    sicang1_path = REPO_ROOT / "sicang5/sicang5_1.txt"
    with open(sicang1_path, "w", encoding="utf-8") as f:
        f.write("# 一简\n")
        for letter in "abcdefghijklmnopqrstuvwxy":
            elite = final_version.get(letter, "")
            if elite:
                f.write(f"{elite}\t{letter}\n")
    print(f"一简方案已更新: {sicang1_path}")
if __name__ == "__main__":
    main()
