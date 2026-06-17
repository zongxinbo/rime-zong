from __future__ import annotations


HAN_RANGES: tuple[tuple[int, int], ...] = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B739),
    (0x2B740, 0x2B81D),
    (0x2B820, 0x2CEA1),
    (0x2CEB0, 0x2EBE0),
    (0x2EBF0, 0x2EE5F),
    (0x2F800, 0x2FA1F),
    (0x30000, 0x3134A),
    (0x31350, 0x323AF),
)


def is_han_char(text: str) -> bool:
    if len(text) != 1:
        return False
    cp = ord(text)
    return any(start <= cp <= end for start, end in HAN_RANGES)


def is_extended_cjk(text: str) -> bool:
    """判断是否会被 librime 默认 charset_filter 视为扩展汉字。"""
    if len(text) != 1:
        return False
    cp = ord(text)
    return (
        (0x3400 <= cp <= 0x4DBF)
        or (0x20000 <= cp <= 0x2A6DF)
        or (0x2A700 <= cp <= 0x2B73F)
        or (0x2B740 <= cp <= 0x2B81F)
        or (0x2B820 <= cp <= 0x2CEAF)
        or (0x2CEB0 <= cp <= 0x2EBEF)
        or (0x30000 <= cp <= 0x3134F)
        or (0x31350 <= cp <= 0x323AF)
        or (0x2EBF0 <= cp <= 0x2EE5F)
        or (0x323B0 <= cp <= 0x3347F)
        or (0xF900 <= cp <= 0xFAFF)
        or (0x2F800 <= cp <= 0x2FA1F)
    )


def is_common_han_char(text: str) -> bool:
    """判断是否为 Rime extended_charset 关闭时可见的常用汉字。"""
    if not is_han_char(text):
        return False
    return not is_extended_cjk(text)


def gb2312_level(text: str) -> int | None:
    """返回 GB2312 汉字级别：1=一级字，2=二级字，None=非 GB2312 汉字。"""
    if len(text) != 1 or not ("\u4e00" <= text <= "\u9fa5"):
        return None
    try:
        encoded = text.encode("gb2312")
    except UnicodeEncodeError:
        return None
    if len(encoded) != 2:
        return None

    row = encoded[0] - 0xA0
    if 16 <= row <= 55:
        return 1
    if 56 <= row <= 87:
        return 2
    return None


def is_gb2312(text: str) -> bool:
    """判断是否为 GB2312 汉字区内的汉字。"""
    return gb2312_level(text) is not None


def is_gbk(text: str) -> bool:
    """判断是否可用 GBK 编码。"""
    try:
        text.encode("gbk")
    except UnicodeEncodeError:
        return False
    return True


def han_charset_priority(text: str) -> int:
    """返回零频候选的汉字常用度优先级，数值越大越优先。"""
    if is_gb2312(text):
        return 700
    if is_gbk(text):
        return 600
    if len(text) != 1:
        return 0
    cp = ord(text)
    # CJK 统一表意文字基本区，最常用的汉字主体区。
    if 0x4E00 <= cp <= 0x9FFF:
        return 500
    # CJK 统一表意文字扩展 A。
    if 0x3400 <= cp <= 0x4DBF:
        return 400
    # CJK 统一表意文字扩展 B。
    if 0x20000 <= cp <= 0x2A6DF:
        return 300
    # CJK 统一表意文字扩展 C。
    if 0x2A700 <= cp <= 0x2B73F:
        return 250
    # CJK 统一表意文字扩展 D。
    if 0x2B740 <= cp <= 0x2B81F:
        return 240
    # CJK 统一表意文字扩展 E。
    if 0x2B820 <= cp <= 0x2CEAF:
        return 230
    # CJK 统一表意文字扩展 F。
    if 0x2CEB0 <= cp <= 0x2EBEF:
        return 220
    # CJK 统一表意文字扩展 I。
    if 0x2EBF0 <= cp <= 0x2EE5F:
        return 210
    # CJK 统一表意文字扩展 G。
    if 0x30000 <= cp <= 0x3134F:
        return 200
    # CJK 统一表意文字扩展 H。
    if 0x31350 <= cp <= 0x323AF:
        return 190
    # CJK 兼容表意文字。
    if 0xF900 <= cp <= 0xFAFF:
        return 100
    # CJK 兼容表意文字补充。
    if 0x2F800 <= cp <= 0x2FA1F:
        return 90
    return 0


def shortcut_charset_allows(text: str, charset: str, *, score: int | float) -> bool:
    """判断字符是否属于简码策略指定的候选字集。"""
    if charset == "all":
        return True
    if charset == "frequency":
        return score > 0
    if charset == "gbk":
        return is_gbk(text)
    if charset == "gb2312":
        return is_gb2312(text)
    raise ValueError("简码字集只能是 all、frequency、gbk 或 gb2312")


def suffix_structure_charset_allows(text: str, charset: str) -> bool:
    """结构后缀候选字集过滤。"""
    if charset == "all":
        return True
    if charset == "gbk":
        return is_gbk(text)
    if charset == "gb2312":
        return is_gb2312(text)
    raise ValueError("--suffix-structure-charset 只能是 all、gbk 或 gb2312")


def is_han_text(text: str) -> bool:
    return bool(text) and all(is_han_char(char) for char in text)
