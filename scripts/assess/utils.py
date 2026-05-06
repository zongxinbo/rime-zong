import os
import json
import re
from pathlib import Path

def parse_rime_dict(dict_path):
    """解析 Rime 字典文件，提取字符和编码"""
    with open(dict_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '...' in content:
        header, body = content.split('...', 1)
    else:
        header, body = "", content
        
    entries = []
    for line in body.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 2:
            char = parts[0]
            code = parts[1]
            weight = 0
            if len(parts) >= 3 and parts[2].isdigit():
                weight = int(parts[2])
            entries.append((char, code, weight))
            
    return header, entries

def is_gb2312(char):
    """判定是否为 GB2312 汉字"""
    try:
        char.encode('gb2312')
        return True
    except UnicodeEncodeError:
        return False

def get_charset_filter(name):
    """
    加载官方字符集过滤列表。
    注意：文件名包含 charset_ 前缀。
    """
    base_path = Path("scripts/assess/data")
    
    # 特殊处理 CJK 范围
    if name in ["CJK_BASIC", "CJK_A", "CJK_B"]:
        def cjk_filter(c):
            if len(c) != 1: return False # 过滤词组
            cp = ord(c)
            if name == "CJK_BASIC": return 0x4E00 <= cp <= 0x9FFF
            if name == "CJK_A": return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            if name == "CJK_B": return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0x20000 <= cp <= 0x2A6DF
        return cjk_filter

    # 根据名称锁定文件
    if name == "GB2312":
        path = base_path / "charset_gb2312.txt"
    elif name == "GUOZI":
        path = base_path / "charset_guozi.txt"
    elif name == "TONGGUI":
        path = base_path / "charset_tonggui.txt"
    else:
        return lambda x: True

    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            # 过滤掉非单字内容（如果有）
            charset = set(c for c in f.read() if not c.isspace())
        return lambda x: x in charset
    
    # 最后的兜底：如果是 GB2312 但找不到文件，用编码判定
    if name == "GB2312":
        return is_gb2312
        
    return lambda x: True

def load_freq(path):
    """加载字频并归一化"""
    raw = {}
    if not os.path.exists(path):
        return {}, {}
    
    if path.endswith('.json'):
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    else:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    try:
                        char, val = parts[0], float(parts[1])
                        raw[char] = val
                    except ValueError: continue
    
    total = sum(raw.values())
    if total == 0: return {}, {}
    norm = {k: v/total for k, v in raw.items()}
    return norm, raw

def merge_freq(sc_norm, tc_norm):
    """合并归一化后的频率，取较大值"""
    merged = sc_norm.copy()
    for char, freq in tc_norm.items():
        if char not in merged or freq > merged[char]:
            merged[char] = freq
    return merged, merged
