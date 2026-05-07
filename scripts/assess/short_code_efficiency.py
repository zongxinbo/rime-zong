import argparse
from collections import defaultdict
from utils import parse_rime_dict, is_gb2312, load_freq

def get_actual_codes(dict_path, max_length=4, _preloaded_entries=None):
    """
    严格还原 yuhao-assess 的 codeTableService.ts 逻辑
    """
    if _preloaded_entries is not None:
        entries = _preloaded_entries
    else:
        _, entries = parse_rime_dict(dict_path)
    
    # yuhao-assess 逻辑：按文件顺序处理
    full_map = {}   # char -> code
    short_map = {}  # char -> code
    full_pos = {}   # char -> pos
    short_pos = {}  # char -> pos
    
    # 记录每个编码下字符的出现顺序
    code_char_positions = defaultdict(dict) # code -> char -> pos
    code_counts = defaultdict(int)
    
    for char, code, _ in entries:
        if len(char) != 1: continue
        
        # 计算该字符在该编码下的位置
        if char not in code_char_positions[code]:
            code_counts[code] += 1
            code_char_positions[code][char] = code_counts[code]
        
        pos = code_char_positions[code][char]
        
        if char not in full_map:
            full_map[char] = code
            short_map[char] = code
            full_pos[char] = pos
            short_pos[char] = pos
        else:
            # 只有严格更长才更新 full
            if len(code) > len(full_map[char]):
                full_map[char] = code
                full_pos[char] = pos
            # 只有严格更短才更新 short
            if len(code) < len(short_map[char]):
                short_map[char] = code
                short_pos[char] = pos

    def apply_selection(code, pos):
        if pos == 1:
            if len(code) < max_length:
                return code + "_"
            return code
        return code + str(pos)

    char_to_final_full = {c: apply_selection(full_map[c], full_pos[c]) for c in full_map}
    char_to_final_short = {c: apply_selection(short_map[c], short_pos[c]) for c in short_map}
    
    return char_to_final_short, char_to_final_full

def analyze_top_n_efficiency(dict_path, freq_data, top_n, charset_filter=is_gb2312, max_length=4, _preloaded_entries=None, _preloaded_actual_codes=None):
    if _preloaded_actual_codes is not None:
        char_to_short, char_to_full = _preloaded_actual_codes
    else:
        char_to_short, char_to_full = get_actual_codes(dict_path, max_length=max_length, _preloaded_entries=_preloaded_entries)
    
    processed = []
    for char, freq in freq_data.items():
        if freq <= 0 or not charset_filter(char): continue
        short = char_to_short.get(char)
        full = char_to_full.get(char)
        if not short or not full: continue
        
        sl, fl = len(short), len(full)
        processed.append({
            'char': char, 'sl': sl, 'fl': fl, 'freq': freq,
            'gain_product': freq * (fl - sl)
        })

    # 只要实际首选短码比全码短，就纳入 Top-N 收益排序。
    # Wucang5 的三简/四简会在计入选择键后达到 4 码；如果再限制 sl < max_length，
    # 表格会在 500 档附近提前饱和，看不到 1000+ 简码层的收益曲线。
    shortcuts = [p for p in processed if p['sl'] < p['fl']]
    sorted_by_gain = sorted(shortcuts, key=lambda x: x['gain_product'], reverse=True)
    
    top_chars = set(p['char'] for p in sorted_by_gain[:top_n])
    
    tw, tf = 0.0, 0.0
    for p in processed:
        length = p['sl'] if p['char'] in top_chars else p['fl']
        tw += p['freq'] * length
        tf += p['freq']
        
    return tw / tf if tf > 0 else 0.0

def analyze_efficiency(dict_path, freq_data, charset_filter=is_gb2312, max_length=4, _preloaded_entries=None):
    char_to_short, char_to_full = get_actual_codes(dict_path, max_length=max_length, _preloaded_entries=_preloaded_entries)
    valid_chars = [c for c in char_to_full.keys() if c in freq_data and charset_filter(c)]
    
    res = {}
    for mode in ['full', 's1', 's2', 'all']:
        tw, tf = 0.0, 0.0
        for char in valid_chars:
            freq = freq_data[char]
            short, full = char_to_short[char], char_to_full[char]
            if mode == 'full': l = len(full)
            elif mode == 's1': l = len(short) if len(short) <= 2 else len(full) # 包含键
            elif mode == 's2': l = len(short) if len(short) <= 3 else len(full) # 包含键
            else: l = len(short)
            tw += freq * l
            tf += freq
        res[mode] = tw / tf if tf > 0 else 0
    return res
