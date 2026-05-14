import argparse
import json
from collections import defaultdict
from utils import parse_rime_dict, is_gb2312, load_freq, is_explicit_completion_code

def load_equiv_table(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = json.load(f)
        return content.get("data", content)

def get_actual_codes(dict_path, max_length=4, _preloaded_entries=None):
    """
    回归到第 18 轮的纯粹逻辑：
    1. 完全基于物理行号顺序。
    2. pos 1 补空格，pos > 1 加数字。
    3. 简码选取字典中该字出现的【最后一个】编码。
    """
    if _preloaded_entries is not None:
        entries = _preloaded_entries
    else:
        _, entries = parse_rime_dict(dict_path)
    
    code_counts = defaultdict(int)
    code_char_positions = defaultdict(dict)
    char_to_final_codes = {}
    
    for char, code, _ in entries:
        if len(char) != 1: continue
        
        # 按物理顺序分配位置
        if char not in code_char_positions[code]:
            code_counts[code] += 1
            code_char_positions[code][char] = code_counts[code]
        
        pos = code_char_positions[code][char]
        
        decorated = code
        if pos == 1:
            if len(code) < max_length and not is_explicit_completion_code(code):
                decorated = code + "_"
        else:
            decorated = code + str(pos)
            
        # 记录全码（第一个）和简码（最后一个）
        if char not in char_to_final_codes:
            char_to_final_codes[char] = [decorated, decorated]
        else:
            char_to_final_codes[char][1] = decorated
            
    return char_to_final_codes

def analyze_speed_equivalent(dict_path, freq_data, equiv_table_path, charset_filter=is_gb2312, mode='all', max_length=4, _preloaded_entries=None, _preloaded_actual_codes=None):
    if _preloaded_actual_codes is not None:
        char_all_codes = _preloaded_actual_codes
    else:
        char_all_codes = get_actual_codes(dict_path, max_length=max_length, _preloaded_entries=_preloaded_entries)

    equiv_data = load_equiv_table(equiv_table_path)
    
    target_map = {}
    for char, codes in char_all_codes.items():
        if not charset_filter(char): continue
        full_code, short_code = codes
        if mode == 'full': target_map[char] = full_code
        elif mode == 'all': target_map[char] = short_code
        elif mode == 's1': target_map[char] = short_code if len(short_code.replace('_','')) <= 1 else full_code
        elif mode == 's2': target_map[char] = short_code if len(short_code.replace('_','')) <= 2 else full_code
            
    total_weighted_equiv = 0.0
    total_pair_frequency = 0.0
    for char, code in target_map.items():
        freq = freq_data.get(char, 0)
        if freq <= 0: continue
        for i in range(len(code) - 1):
            pair = code[i:i+2]
            equiv = equiv_data.get(pair)
            if equiv is not None:
                total_weighted_equiv += equiv * freq
                total_pair_frequency += freq
    return total_weighted_equiv / total_pair_frequency if total_pair_frequency > 0 else 0.0
