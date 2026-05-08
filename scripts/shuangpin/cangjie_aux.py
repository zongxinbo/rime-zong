import os
from collections import defaultdict

def get_cangjie_mapping(cangjie_path='../../schemas/cangjie/cangjie5/cangjie5.dict.yaml'):
    """
    Reads the Cangjie5 dictionary and returns a mapping from character to its 
    list of first+last codes (prioritizing codes that do not start with z or x).
    Returns: { char: [code1, code2, ...] }
    """
    char_raw_codes = defaultdict(list)
    with open(cangjie_path, 'r', encoding='utf-8') as f:
        in_body = False
        for line in f:
            if line.strip() == '...':
                in_body = True
                continue
            if not in_body or not line.strip() or line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                char, code = parts[0], parts[1]
                char_raw_codes[char].append(code)
    
    mapping = {}
    for char, codes in char_raw_codes.items():
        preferred_shorts = []
        other_shorts = []
        for code in codes:
            # 提取首尾码
            short = code[0] + code[-1] if len(code) > 1 else code
            if not code.startswith('z') and not code.startswith('x'):
                if short not in preferred_shorts:
                    preferred_shorts.append(short)
            else:
                # 只有在非 z/x 列表中没出现过才加入
                if short not in other_shorts and short not in preferred_shorts:
                    other_shorts.append(short)
        
        all_shorts = preferred_shorts + other_shorts
        if all_shorts:
            mapping[char] = all_shorts
            
    return mapping
