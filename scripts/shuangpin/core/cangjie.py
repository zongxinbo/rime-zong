from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .io import iter_rime_dict_rows
from .models import DictEntry
from .paths import CANGJIE5_DICT


LOW_PRIORITY_PREFIXES = ("x", "z")

# 这里过滤的是“可以作为码表正文的 CJK 文字字符”，不是狭义的
# “统一汉字”。仓颉五代表里除了常规汉字，还包含康熙部首、
# CJK 部首补充、CJK 笔画，以及不断新增的扩展汉字。它们应当
# 进入仓颉兜底和辅助码来源；全角标点、空格、括号等符号则不应进入。
CJK_TEXT_RANGES = (
    (0x2E80, 0x2EFF),   # CJK 部首补充，例如 ⺁、⺄。
    (0x2F00, 0x2FDF),   # 康熙部首，例如 ⼀、⾔。
    (0x31C0, 0x31EF),   # CJK 笔画，例如 ㇆、㇚。
    (0x3400, 0x4DBF),   # CJK 统一汉字扩展 A。
    (0x4E00, 0x9FFF),   # CJK 统一汉字基本区。
    (0xF900, 0xFAFF),   # CJK 兼容汉字。
    (0x20000, 0x3FFFD), # CJK 扩展汉字大区，覆盖 B 及之后的新扩展和兼容补充区。
)

CJK_TEXT_CHARS = {
    "々", # 汉字迭代记号。
    "〆", # 日文中作为文字使用的締字略符，仓颉表中按文字处理。
    "〇", # 汉字数字零。
    "〻", # 竖排汉字迭代记号。
}


def iter_cangjie_code_rows(path: Path = CANGJIE5_DICT):
    """按源码表顺序逐行产出可用的单字符仓颉码。

    这里不先按“字”聚合，是因为最终仓颉兜底需要保留同一个字的多个
    正常编码，例如“哥”在仓颉五代原表中同时有 `mrmnr` 和 `mrnr`。
    """

    for order, parts in enumerate(iter_rime_dict_rows(path)):
        if len(parts) < 2:
            continue
        text, code = parts[0], parts[1]
        if is_han_char(text) and code:
            yield order, text, code


def is_han_char(text: str) -> bool:
    """判断一个字符是否可以进入本方案的汉字/部件码表。

    函数名保留为 is_han_char 是为了兼容其他模块已有调用；实际语义
    是“CJK 文字字符”，包含汉字、部首、笔画和少量文字性符号。
    """

    if len(text) != 1:
        return False
    if text in CJK_TEXT_CHARS:
        return True
    codepoint = ord(text)
    return any(start <= codepoint <= end for start, end in CJK_TEXT_RANGES)


def load_cangjie_codes(path: Path = CANGJIE5_DICT) -> dict[str, list[str]]:
    """读取仓颉五代码表，只保留可作为正文文字的单字符条目。"""

    codes: dict[str, list[str]] = defaultdict(list)
    for _order, text, code in iter_cangjie_code_rows(path):
        codes[text].append(code)
    return codes


def choose_cangjie_code(codes: list[str]) -> str:
    """从同一字符的多个仓颉码中选择主码。

    仓颉原表里 `x`、`z` 开头的编码多为兼容、符号或特殊区编码；
    作为辅助码时优先使用正常仓颉码，只有没有正常码时才退回它们。
    """

    for code in codes:
        if not code.startswith(LOW_PRIORITY_PREFIXES):
            return code
    return codes[0]


def load_aux_map(path: Path = CANGJIE5_DICT) -> dict[str, str]:
    """生成单字音形方案使用的两位仓颉辅助码。

    辅助码取仓颉码的首尾两码；如果某字仓颉码只有一位，就在末尾补 `z`，
    保证“二码双拼 + 两位辅助码”的单字全码恒为四码，同时避免 `十=uijj`
    这种重复补位造成的手感误导。
    """

    raw = load_cangjie_codes(path)
    aux: dict[str, str] = {}
    for text, codes in raw.items():
        code = choose_cangjie_code(codes)
        aux[text] = code + "z" if len(code) == 1 else code[0] + code[-1]
    return aux


def load_aux_lists(path: Path = CANGJIE5_DICT) -> dict[str, list[str]]:
    """生成手心输入法挂接辅助码所需的完整首尾码列表。

    手心挂接文件需要保留同一字的多个辅助码：正常仓颉码排在前面，
    `x`、`z` 开头的兼容码排在后面；一位仓颉码也补 `z`，与 Rime
    主方案的两位辅助码规则保持一致。
    """

    raw = load_cangjie_codes(path)
    mapping: dict[str, list[str]] = {}
    for text, codes in raw.items():
        preferred: list[str] = []
        fallback: list[str] = []
        for code in codes:
            aux = code[0] + code[-1] if len(code) > 1 else code + "z"
            if code.startswith(LOW_PRIORITY_PREFIXES):
                if aux not in preferred and aux not in fallback:
                    fallback.append(aux)
            elif aux not in preferred:
                preferred.append(aux)
        auxes = preferred + fallback
        if auxes:
            mapping[text] = auxes
    return mapping


def build_prefixed_cangjie_entries(
    path: Path = CANGJIE5_DICT,
    prefix: str = "o",
    weight: int = -1000000,
    tier: int = 90,
) -> list[DictEntry]:
    """生成最终码表里的仓颉兜底条目。

    仓颉码使用 `o + 仓颉码`。条目顺序保留仓颉五代原表的字符顺序，
    同码时不再按字符文本重排；是否需要补 `z` 直达码由最终合表阶段
    根据实际重码情况判断。
    """

    entries: list[DictEntry] = []
    seen: set[tuple[str, str]] = set()
    for order, text, code in iter_cangjie_code_rows(path):
        out_code = prefix + code
        key = (text, out_code)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            DictEntry(
                text=text,
                code=out_code,
                weight=weight,
                tier=tier,
                source="cangjie",
                order=order,
            )
        )
    return entries
