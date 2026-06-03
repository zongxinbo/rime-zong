#!/usr/bin/env python3
# encoding: utf-8
"""
纯算法生成 z?/x? 固定二简避重码表 (fixed_prefix_code.txt)
根据可选权重模式归一化字频挑选 52 个最需要救援的繁简常用字，
并根据首键优先、尾键其次的可记忆锚点进行键位映射；无首尾匹配则放弃。
"""

import sys
import argparse
from pathlib import Path
from collections import defaultdict

# 导入核心依赖
sys.path.append(str(Path(__file__).resolve().parent.parent))
from core.cangjie_builder import (
    CANGJIE5_DICT_PATH,
    ONE_CODE_PATH,
    ROOT_CODE_PATH,
    FIXED_PREFIX_CODE_PATH,
    get_weighted_frequencies,
    parse_cangjie_dict,
    is_han_char,
)
from core.glyph_codes import filter_glyph_preferred_entries
from core.weight_profiles import WEIGHT_PROFILES, get_weight_profile

def load_excluded_chars() -> set[str]:
    """加载需要排除的一简字和字根字。"""
    excluded = set()
    
    # 1. 一简已占字
    if ONE_CODE_PATH.exists():
        for line in ONE_CODE_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 1:
                    excluded.add(parts[0])
                    
    # 2. 字根字/特殊键本体字
    if ROOT_CODE_PATH.exists():
        for line in ROOT_CODE_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 1:
                    excluded.add(parts[0])
                    
    return excluded

def load_excluded_codes() -> set[str]:
    """加载已被占用的 z? 或 x? 二码编码。"""
    excluded = set()
    if ROOT_CODE_PATH.exists():
        for line in ROOT_CODE_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 2:
                    code = parts[1]
                    if len(code) == 2 and code.startswith(("z", "x")):
                        excluded.add(code)
    return excluded

def main():
    parser = argparse.ArgumentParser(description="生成 z?/x? 固定二简避重码表")
    parser.add_argument("--weights", choices=tuple(WEIGHT_PROFILES), default="sc_daily",
                        help="字频权重模式；默认 sc_daily")
    args = parser.parse_args()

    print("==================================================")
    print("开始生成算法版 z?/x? 避重简码...")
    
    # 1. 加载归一化字频模型
    print(f"正在加载归一化加权字频 ({args.weights})...")
    weights = get_weight_profile(args.weights)
    char_freqs = get_weighted_frequencies(weights)
    
    # 2. 读取排他字集
    excluded = load_excluded_chars()
    excluded_codes = load_excluded_codes()
    print(f"已加载排他字集 (一简与字根字)：共 {len(excluded)} 个字")
    print(f"已加载排他编码：{excluded_codes}")
    
    # 3. 解析原始仓颉全码字典，计算重码组与候选深度
    print(f"正在读取原始全码字典: {CANGJIE5_DICT_PATH} ...")
    entries = filter_glyph_preferred_entries(parse_cangjie_dict(CANGJIE5_DICT_PATH), args.weights)
    
    # 统计每个字对应的全码（取第一个/最短的全码用来做联想映射）
    char_to_code = {}
    code_to_chars = defaultdict(list)
    
    for entry in entries:
        if not is_han_char(entry.text):
            continue
        # 排除以 z 或 x 开头的特种编码
        if entry.code.startswith(("z", "x")):
            continue
        if entry.text not in char_to_code or len(entry.code) < len(char_to_code[entry.text]):
            char_to_code[entry.text] = entry.code
        # 归纳到重码桶中
        if entry.text not in code_to_chars[entry.code]:
            code_to_chars[entry.code].append(entry.text)
            
    # 按字频对每个编码桶中的候选字进行降序重排，以模拟真实输入候选项顺序
    code_to_chars_sorted = {}
    char_depths = {}
    
    for code, chars in code_to_chars.items():
        sorted_chars = sorted(chars, key=lambda c: char_freqs.get(c, 0), reverse=True)
        code_to_chars_sorted[code] = sorted_chars
        for index, char in enumerate(sorted_chars):
            char_depths[char] = index + 1 # 候选深度从 1 开始
            
    # 4. 执行避重痛点字打分与挑选
    candidates = []
    for char, code in char_to_code.items():
        if char in excluded:
            continue
            
        freq = char_freqs.get(char, 0)
        depth = char_depths.get(char, 1)
        
        # 严格过滤：只选择在全码位置需要选重的字 (depth >= 2)
        if depth < 2:
            continue
            
        # 评分公式：字频 * (候选深度 - 1)
        # 深度越深且字频越高的字，其痛点值（避重收益）越大
        score = freq * (depth - 1)
        
        # [核心战略加成]：如果全码是 4 码，且前 3 码的所有 26 个位置在字典里全都被占满了，
        # 则该字在 4 码内物理上绝对无法消重，属于最绝望重码字。强行保送避重二码！
        if len(code) == 4:
            prefix3 = code[:3]
            occupied_count = sum(1 for c in code_to_chars if len(c) == 4 and c.startswith(prefix3))
            if occupied_count >= 26:
                score += 5000000
            elif occupied_count >= 24:
                score += 2000000
                
        candidates.append((score, char, code, depth, freq))
        
    # 按评分从高到低排序，挑选前 50 个高价值痛点字
    candidates.sort(key=lambda x: x[0], reverse=True)
    top_50 = candidates[:50]
    
    print("\n[高价值避重候选字 Top 10]:")
    for i, (score, char, code, depth, freq) in enumerate(top_50[:10], 1):
        print(f"  No.{i}: {char} (全码:{code}, 候选顺位:{depth}, 归一化字频:{freq:.6f}, 避重得分:{score:.2f})")
        
    # 5. 执行首尾锚点映射分配算法 (首键 -> 尾键)
    # 初始化 50 个可用槽位 (排除已占用的 xz, zz)
    letters = "abcdefghijklmnopqrstuvwxyz"
    all_slots = []
    for prefix in ("z", "x"):
        for suffix in letters:
            slot = prefix + suffix
            if slot not in excluded_codes:
                all_slots.append(slot)
            
    slot_to_char = {}
    char_to_slot = {}
    
    skipped_chars = []
    
    for score, char, code, depth, freq in top_50:
        if not code:
            skipped_chars.append(char)
            continue
            
        assigned = False
        
        # --- 规则 1：首键映射 ---
        first_key = code[0]
        for prefix in ("z", "x"):
            candidate_slot = prefix + first_key
            if candidate_slot in all_slots and candidate_slot not in slot_to_char:
                slot_to_char[candidate_slot] = char
                char_to_slot[char] = candidate_slot
                assigned = True
                break
        if assigned:
            continue
            
        # --- 规则 2：尾键映射 ---
        last_key = code[-1]
        for prefix in ("z", "x"):
            candidate_slot = prefix + last_key
            if candidate_slot in all_slots and candidate_slot not in slot_to_char:
                slot_to_char[candidate_slot] = char
                char_to_slot[char] = candidate_slot
                assigned = True
                break
        if assigned:
            continue
            
        skipped_chars.append(char)

    empty_slots = [slot for slot in all_slots if slot not in slot_to_char]
    print(f"\n首尾锚点映射后，剩余未分配槽位 {len(empty_slots)} 个，无首尾匹配或槽位冲突放弃 {len(skipped_chars)} 个字")
        
    # 7. 整理并写入 fixed_prefix_code.txt
    print(f"正在写入原型文件: {FIXED_PREFIX_CODE_PATH} ...")
    FIXED_PREFIX_CODE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    output_lines = ["# 算法版 z?/x? 避重二码直达表"]
    # 按键位字母表顺序输出
    sorted_slots = sorted(slot_to_char.keys())
    
    for slot in sorted_slots:
        char = slot_to_char[slot]
        output_lines.append(f"{char}\t{slot}")
        
    FIXED_PREFIX_CODE_PATH.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    print(f"成功！已分配 {len(slot_to_char)} 个槽位。原型文件已保存。")
    print("==================================================")

if __name__ == "__main__":
    main()
