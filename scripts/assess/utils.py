import os
import json
import re
from pathlib import Path


def is_explicit_commit_code(code, commit_suffixes=None):
    """判断编码末键是否已经承担确认或选重功能。"""
    if not code:
        return False
    if code[-1].isdigit():
        return True
    return bool(commit_suffixes) and code[-1] in set(commit_suffixes)


def normalize_code(code):
    """规范化码表编码字段。

    有些导入码表会把冗余全码写成 `kai[k1]` 这类形式，其中方括号内
    是简码提示，并不是用户实际输入的按键。测评时只保留 `[` 之前的
    真实编码。
    """
    return code.split('[', 1)[0]


def infer_max_code_length(entries, default=4, commit_suffixes=None):
    """根据单字条目自动推断方案最大码长。

    Rime 码表可能包含词组码、符号辅助码或显式选重码，这些条目不一定
    代表单字方案的真实最大码长。测评时只看单字编码，并排除末尾数字
    这类已经承担选重/确认功能的编码。参数化的上屏末字母仍按编码本身
    计入最大码长，只影响后续是否补空格。
    """
    lengths = [
        len(code)
        for text, code, _ in entries
        if len(text) == 1 and code and not is_explicit_commit_code(code)
    ]
    if not lengths:
        return default
    return max(lengths)

def is_cjk_text(text):
    """判断字段是否像汉字/词条字段。"""
    for char in text:
        cp = ord(char)
        if (
            0x3400 <= cp <= 0x4DBF
            or 0x4E00 <= cp <= 0x9FFF
            or 0x20000 <= cp <= 0x2A6DF
            or 0x2A700 <= cp <= 0x2B73F
            or 0x2B740 <= cp <= 0x2B81F
            or 0x2B820 <= cp <= 0x2CEAF
            or 0x2CEB0 <= cp <= 0x2EBEF
            or 0x30000 <= cp <= 0x3134F
            or 0xF900 <= cp <= 0xFAFF
            or cp in (0x3005, 0x3007)
        ):
            return True
    return False


def split_dict_line(line):
    """拆分码表行，兼容 Tab 与空格分隔。"""
    return line.split()


def parse_entry_fields(parts):
    """从字段中识别词条和编码，兼容 `字 码` 与 `码 字`。"""
    text, code = parts[0], parts[1]
    first_is_text = is_cjk_text(text)
    second_is_text = is_cjk_text(code)
    if second_is_text and not first_is_text:
        text, code = code, text
    return text, normalize_code(code)


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
        parts = split_dict_line(line)
        if len(parts) >= 2:
            char, code = parse_entry_fields(parts)
            weight = 0
            for part in parts[2:]:
                if part.isdigit():
                    weight = int(part)
                    break
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
