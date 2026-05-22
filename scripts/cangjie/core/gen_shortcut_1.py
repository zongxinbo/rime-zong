"""
Sicang5 一简（One-Code）方案设计脚本

本脚本用于对比不同字频表下的一简分配方案，并生成建议稿。

算法核心逻辑：
1. get_one_codes (纯算法):
   - 基于单一语料库（字频表）计算。
   - Tier 1 (StartsWith): 优先寻找以该字母开头的最高频汉字。
   - Tier 2 (Contains): 如果 Top 100 高频字中存在包含该字母的字，且频次超过首码匹配字的 1.8 倍，则允许抢位。

2. get_final_version (最终版):
   - 以“Dialogue”（口语语料）为基底，确保口语常用字绝对优先。
   - 权重分配: Dialogue(6), Subtlex(5), Zhihu(4), BLCU(2), Essay(1)。
   - 修正机制：
     a) 加权修正: 若任一其他语料推荐的字，其加权总分超过基底字的倍数阈值，则修正。
     b) 首码保护: 若基底字是首码匹配而修正字不是，则需 2.5 倍频次差才允许替换；否则为 1.2 倍。
     c) 校准保护: 对低收益两码字抢高价值字根位的情况，按频率倍数、省码收益和字根位代价人工校准。
"""

import sys
from pathlib import Path
from collections import defaultdict

sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.cangjie_builder import (
    parse_cangjie_dict,
    parse_frequency_file,
    is_han_char,
    REPO_ROOT,
    FREQ_PATHS,
    FREQ_WEIGHTS
)

LETTERS = "abcdefghijklmnopqrstuvwxy"

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

    for letter in LETTERS:
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
            if char_rank > 100:
                break
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


def get_shortest_code(char_codes, char):
    codes = char_codes.get(char, [])
    if not codes:
        return ""
    return min(codes, key=lambda code: (len(code), code))


def get_score(char_scores, char):
    return char_scores.get(char, 0)


def one_code_benefit(char_scores, char_codes, char):
    code = get_shortest_code(char_codes, char)
    return get_score(char_scores, char) * max(len(code) - 1, 0)


def apply_protected_map(elite, protected_map, char_codes):
    """把明确校准位写入 elite，并保证同字只出现一次。"""
    for key, value in protected_map.items():
        if value not in char_codes:
            continue
        old_key = next((k for k, v in elite.items() if v == value), None)
        if old_key:
            elite.pop(old_key)
        elite[key] = value
    return elite


def get_final_version(char_codes, all_freqs, results):
    """最终版：以口语语料（Dialogue）为基底，利用多源加权总分进行修正。"""

    weights = FREQ_WEIGHTS

    char_scores = {}
    for char in char_codes:
        score = sum(all_freqs[src].get(char, 0) * w for src, w in weights.items() if src in all_freqs)
        if score > 0:
            char_scores[char] = score

    # 强制保护/优先分配。
    # g/l/p/r 是按“频率倍数 + 省码收益 + 字根位代价”从原表校准：
    #   g: 去 -> 地；l: 个 -> 中；p: 也 -> 心；r: 只 -> 和。
    protected_map = {
        'a': '是', 'd': '来', 't': '着', 'g': '地',
        'k': '在', 'f': '你', 'h': '的', 'i': '我',
        'l': '中', 'm': '一', 'o': '人', 'p': '心',
        'r': '和', 'v': '好', 'x': '以'
    }

    # 默认以最高权重的纯口语语料结果为基底
    elite = dict(results["Dialogue"])
    elite = apply_protected_map(elite, protected_map, char_codes)

    used_chars = set(elite.values())

    # 综合得分修正
    for letter in LETTERS:
        # 保护位不参与被抢占
        if letter in protected_map:
            continue

        base_char = elite.get(letter, "")
        base_score = char_scores.get(base_char, 0)

        candidates = set()
        for src, res in results.items():
            c = res.get(letter, "")
            # 过滤掉一些不适合做一简的语气词（可选）
            if c == '哈' and letter == 'r':
                continue
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
                            if other_key in code:
                                base_valid_for_other = True
                                break

                        if base_valid_for_other:
                            elite[letter] = cand
                            elite[other_key] = base_char
                            break

    return elite, char_scores, protected_map


def main():
    source = REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml"
    freq_paths = FREQ_PATHS

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
    current_path = REPO_ROOT / "scripts/cangjie/prototypes/one_code.txt"
    if current_path.exists():
        with open(current_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) == 2:
                    current_codes[parts[1]] = parts[0]

    if "Dialogue" in results:
        final_version, char_scores, protected_map = get_final_version(char_codes, all_freqs, results)
    else:
        final_version, char_scores, protected_map = {}, {}, {}
        print("Error: Required Dialogue frequencies missing.")

    output_path = REPO_ROOT / "scripts/cangjie/prototypes/one_code_report.md"
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 一简方案分配对比表\n\n")
        f.write("本表对比了：\n")
        f.write("1. **纯算法**：基于五份字频表各自独立计算。\n")
        f.write("2. **当前正式版**：当前使用的校准方案。\n")
        f.write("3. **最终版**：以最高权重的口语语料(Dialogue)为基底，当其他语料出现综合加权更高分的字时触发自动修正，支持换位策略。\n\n")

        f.write("| 键位 | Dialogue (纯算法) | Subtlex (纯算法) | Zhihu (纯算法) | BLCU (纯算法) | Essay (纯算法) | 当前正式版 | **最终版** |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for letter in LETTERS:
            d = results.get("Dialogue", {}).get(letter, "")
            s = results.get("Subtlex", {}).get(letter, "")
            z = results.get("Zhihu", {}).get(letter, "")
            b = results.get("BLCU", {}).get(letter, "")
            e = results.get("Essay", {}).get(letter, "")
            curr = current_codes.get(letter, "")
            elite = final_version.get(letter, "")
            f.write(f"| {letter} | {d} | {s} | {z} | {b} | {e} | {curr} | **{elite}** |\n")

        f.write("\n## 校准位说明\n\n")
        f.write("| 键位 | 字 | 全码 | 综合字频 | 省键收益 | 说明 |\n")
        f.write("|---|---|---|---:|---:|---|\n")
        notes = {
            'g': '去/地频率差距仅 1.36x，但地多省一键，综合收益更高。',
            'l': '个只省一键，且对中只有 2.84x 频率优势，不足以稳定抢位。',
            'p': '也只省一键，且对心只有 1.95x 频率优势，不足以稳定抢位。',
            'r': '和比只更高频，且全码更长，省码收益明显更高。',
        }
        for key in ['g', 'l', 'p', 'r']:
            char = protected_map[key]
            code = get_shortest_code(char_codes, char)
            score = get_score(char_scores, char)
            benefit = one_code_benefit(char_scores, char_codes, char)
            f.write(f"| {key} | {char} | {code} | {int(score)} | {int(benefit)} | {notes[key]} |\n")
    print(f"对比结果已保存至: {output_path}")

    # 同时更新实际的一简方案文件
    one_code_path = REPO_ROOT / "scripts/cangjie/prototypes/one_code.txt"
    with open(one_code_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# 一简\n")
        for letter in LETTERS:
            elite = final_version.get(letter, "")
            if elite:
                f.write(f"{elite}\t{letter}\n")
    print(f"一简方案已更新: {one_code_path}")


if __name__ == "__main__":
    main()
