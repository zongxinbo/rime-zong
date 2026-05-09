import os
from collections import defaultdict

def get_cangjie_mapping(cangjie_path='../../schemas/cangjie/cangjie5/cangjie5.dict.yaml'):
    """读取仓颉五代码表，生成“字 -> 首尾辅助码列表”的映射。

    同一个字可能有多个仓颉码。为了贴近日常输入，普通仓颉码的
    首尾码排在前面；`z`、`x` 开头的兼容码排在后面作为补充。
    返回格式：{字: [辅助码1, 辅助码2, ...]}。
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
