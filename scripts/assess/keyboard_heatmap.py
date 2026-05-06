import argparse
from collections import defaultdict
from utils import parse_rime_dict, is_gb2312, load_freq
from speed_equivalent import get_actual_codes

# 严格对齐 yuhao-assess 的手指映射
FINGER_MAPPING = {
    '1': '左小指', 'q': '左小指', 'a': '左小指', 'z': '左小指',
    '2': '左无名指', 'w': '左无名指', 's': '左无名指', 'x': '左无名指',
    '3': '左中指', 'e': '左中指', 'd': '左中指', 'c': '左中指',
    '4': '左食指', '5': '左食指', 'r': '左食指', 't': '左食指', 'f': '左食指', 'g': '左食指', 'v': '左食指', 'b': '左食指',
    '6': '右食指', '7': '右食指', 'y': '右食指', 'u': '右食指', 'h': '右食指', 'j': '右食指', 'n': '右食指', 'm': '右食指',
    '8': '右中指', 'i': '右中指', 'k': '右中指', ',': '右中指',
    '9': '右无名指', 'o': '右无名指', 'l': '右无名指', '.': '右无名指',
    '0': '右小指', 'p': '右小指', ';': '右小指', "'": '右小指', '/': '右小指',
    '-': '右小指', '=': '右小指', '[': '右小指', ']': '右小指',
    ' ': '双拇指'
}

ROW_MAPPING = {
    '1': '数字排', '2': '数字排', '3': '数字排', '4': '数字排', '5': '数字排',
    '6': '数字排', '7': '数字排', '8': '数字排', '9': '数字排', '0': '数字排',
    'q': '上排', 'w': '上排', 'e': '上排', 'r': '上排', 't': '上排',
    'y': '上排', 'u': '上排', 'i': '上排', 'o': '上排', 'p': '上排',
    'a': '中排', 's': '中排', 'd': '中排', 'f': '中排', 'g': '中排',
    'h': '中排', 'j': '中排', 'k': '中排', 'l': '中排', ';': '中排', "'": '中排',
    'z': '下排', 'x': '下排', 'c': '下排', 'v': '下排', 'b': '下排',
    'n': '下排', 'm': '下排', ',': '下排', '.': '下排', '/': '下排',
    ' ': '空格排'
}

PUNCTUATION_KEYS = {
    ';': 0.1,
    ',': 0.4,
    '.': 0.4,
    '/': 0.05,
    "'": 0.05,
}
PUNCTUATION_CHAR_RATIO = 0.13

def analyze_heatmap(dict_path, freq_path, charset_filter=is_gb2312, _preloaded_freq=None, max_length=4, simulate_punctuation=False, _preloaded_entries=None):
    char_all_codes = get_actual_codes(dict_path, max_length=max_length, _preloaded_entries=_preloaded_entries)
    
    if _preloaded_freq is not None:
        freqs = _preloaded_freq
    else:
        freqs, _ = load_freq(freq_path)
    
    key_distribution = defaultdict(float)
    total_weighted_usage = 0.0
    
    total_code_length = 0
    total_codes = 0

    for char, codes in char_all_codes.items():
        if not charset_filter(char): continue
        weight = freqs.get(char, 0.0)
        
        # 统计平均码长
        # codes[0] 是全码，codes[1] 是简码
        code_to_stat = codes[1] # 默认分析简码
        
        total_code_length += len(code_to_stat.replace('_','')) # 统计原始按键长
        total_codes += 1
            
        if weight <= 0: continue
        
        for char_in_code in code_to_stat.lower():
            key = char_in_code if char_in_code != '_' else ' '
            key_distribution[key] += weight
            total_weighted_usage += weight
                
    if total_weighted_usage == 0:
        return None

    final_frequencies = {}
    if simulate_punctuation:
        avg_code_len = total_code_length / total_codes if total_codes > 0 else 2
        punct_ratio = PUNCTUATION_CHAR_RATIO
        hanzi_ratio = 1 - punct_ratio
        punct_key_ratio = punct_ratio / (punct_ratio + hanzi_ratio * avg_code_len)
        remaining_ratio = 1 - punct_key_ratio
        
        all_keys = set(key_distribution.keys()) | set(PUNCTUATION_KEYS.keys())
        for key in all_keys:
            raw_freq = key_distribution.get(key, 0.0) / total_weighted_usage
            compressed_freq = raw_freq * remaining_ratio
            punct_freq_bonus = punct_key_ratio * PUNCTUATION_KEYS.get(key, 0.0)
            final_frequencies[key] = compressed_freq + punct_freq_bonus
    else:
        for key, count in key_distribution.items():
            final_frequencies[key] = count / total_weighted_usage

    finger_load = defaultdict(float)
    row_load = defaultdict(float)
    left_hand = 0.0
    right_hand = 0.0

    for key, freq in final_frequencies.items():
        finger = FINGER_MAPPING.get(key, '未知')
        row = ROW_MAPPING.get(key, '未知')
        
        finger_load[finger] += freq
        row_load[row] += freq
        
        if finger.startswith('左'):
            left_hand += freq
        elif finger.startswith('右'):
            right_hand += weight # BUG FIXED: should be freq!
            # Wait, looking at line 103: right_hand += weight. SHOULD BE freq.
            # I found a bug in my previous thought.
    
    # Let me re-write the loop carefully.
    
    finger_load = defaultdict(float)
    row_load = defaultdict(float)
    left_hand = 0.0
    right_hand = 0.0

    for key, freq in final_frequencies.items():
        finger = FINGER_MAPPING.get(key, '未知')
        row = ROW_MAPPING.get(key, '未知')
        finger_load[finger] += freq
        row_load[row] += freq
        if finger.startswith('左'):
            left_hand += freq
        elif finger.startswith('右'):
            right_hand += freq

    hand_total = left_hand + right_hand
    hand_balance = {
        'left': (left_hand / hand_total * 100) if hand_total > 0 else 0,
        'right': (right_hand / hand_total * 100) if hand_total > 0 else 0
    }

    return {
        'hand_balance': hand_balance,
        'finger_load': {k: v * 100 for k, v in finger_load.items()},
        'row_load': {k: v * 100 for k, v in row_load.items()}
    }
