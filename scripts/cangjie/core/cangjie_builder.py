#!/usr/bin/env python3
"""核心模块：从仓颉五代码表按指定长度规则（三码、四码等）取码生成字典。"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
IDS_PATH = REPO_ROOT / "scripts" / "ids" / "ids.txt"

# IDS 运算符集合
_LR = set("⿰⿲")     # 左右 / 左中右
_UD = set("⿱⿳")     # 上下 / 上中下
_WRAP = set("⿴⿵⿶⿷⿸⿹⿺⿻")  # 包围 / 半包围
FREQ_PATHS = {
    "Dialogue": REPO_ROOT / "schemas/common/frequency/char/sc/dialogue_char_freq.txt",
    "Subtlex": REPO_ROOT / "schemas/common/frequency/char/sc/subtlex_char_freq.txt",
    "Zhihu": REPO_ROOT / "schemas/common/frequency/char/sc/zhihu_char_freq.txt",
    "BLCU": REPO_ROOT / "schemas/common/frequency/char/sc/blcu_char_freq.txt",
    "Essay": REPO_ROOT / "schemas/common/essay-zh-hans.txt"
}
FREQ_WEIGHTS = {"Dialogue": 6, "Subtlex": 5, "Zhihu": 4, "BLCU": 2, "Essay": 1}
DEFAULT_FULLCODE_YIELD_MIN_SCORE = 1000

def generate_dict(
    output_path: Path,
    shortcut_paths: dict,
    source_dict: Path,
    freq_file: Path = None,
    max_code_length: int = 5,
    exclude_extended: bool = False,
    vocabulary: str = None,
    max_phrase_length: int = None,
    min_phrase_weight: int = None,
    only_first_full_code: bool = False,
    char_freqs: dict[str, int] = None,
    fullcode_yield_min_score: float = DEFAULT_FULLCODE_YIELD_MIN_SCORE,
    suffix_z: bool = True,
    suffix_structure: bool = False,
    suffix_structure_charset: str = "gbk",
    suffix_structure_occupied_policy: str = "protect-min-score",
    suffix_structure_protect_min_score: float = 100000,
    suffix_structure_keymap: str = "zxwa",
):
    """生成最终字典。

    支持 Z/S1/S2/S3/S4 简码层级。简码只在自身码位优先；该字的
    全码如果还有未获简码且达到常用门槛的重码字，则让出首选位，避免全码位被冷僻字顶上来。
    """
    print(f"正在解析原始仓颉编码: {source_dict}...")
    raw_entries = parse_cangjie_dict(source_dict)
    char_full_codes = defaultdict(list)
    for e in raw_entries:
        if (is_common_han_char(e.text) if exclude_extended else is_han_char(e.text)) and not (e.code.startswith('z') or e.code.startswith('x')):
            if only_first_full_code and e.text in char_full_codes:
                continue
            char_full_codes[e.text].append(e.code)

    # ── 第一步：加载各层级简码 ──
    print("正在加载简码规则...")
    shortcut_entries = []  # (char, code, priority)
    z_root_chars = set()

    def load_shortcut(path, priority):
        if not path or not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) == 2 and not parts[0].startswith("#"):
                    char, code = parts[0], parts[1]
                    shortcut_entries.append((char, code, priority))
                    if priority == 0:
                        z_root_chars.add(char)

    # 优先级数字越小越靠前
    load_shortcut(shortcut_paths.get('z'), 0)
    load_shortcut(shortcut_paths.get(1), 1)
    load_shortcut(shortcut_paths.get(2), 2)
    load_shortcut(shortcut_paths.get(3), 3)
    load_shortcut(shortcut_paths.get(4), 4)

    # ── 第二步：生成全码条目 ──
    print("正在生成单字...")
    if char_freqs is None:
        char_freqs, _ = parse_frequency_file(freq_file)
    else:
        print("使用预加载的加权字频数据进行排序...")

    used_text_code = set()
    for char, code, _ in shortcut_entries:
        used_text_code.add((char, code))

    fullcode_entries = []  # (char, code, freq)
    for char, full_codes in char_full_codes.items():
        if char in z_root_chars:
            full_codes = [code for code in full_codes if len(code) != 1]
        freq = char_freqs.get(char, 0)
        for full_code in full_codes:
            code_proj = project_code(full_code, max_code_length)
            if (char, code_proj) in used_text_code:
                continue
            used_text_code.add((char, code_proj))
            fullcode_entries.append((char, code_proj, freq))

    # ── 第三步：合并排序输出 ──
    # 排序键设计：
    #   1. 按编码分组
    #   2. 简码条目优先（priority 0-4），然后全码
    #   3. 全码层按字频降序，但已有简码的首选让位给未获简码且达到常用门槛的字
    all_entries = []
    shortcut_chars = {char for char, _, priority in shortcut_entries if priority >= 1}
    fullcode_order = build_fullcode_yield_order(
        fullcode_entries,
        shortcut_chars,
        min_promote_score=fullcode_yield_min_score,
    )

    for char, code, priority in shortcut_entries:
        freq = char_freqs.get(char, 0)
        all_entries.append((code, priority, 0, -freq, char))

    for char, code, freq in fullcode_entries:
        all_entries.append((code, 5, fullcode_order[(char, code)], -freq, char))

    all_entries.sort()
    shortcut_leader_chars = build_shortcut_leader_chars(all_entries)

    suffix_entries = []
    suffix_count = 0
    if suffix_z:
        # ── 第四步：后缀消重（z=第二候选）──
        # 对于重码组，给第2选生成 code+z
        # 跳过加后缀后超过 max_code_length 的情况
        code_groups = defaultdict(list)
        for entry in all_entries:
            code_groups[entry[0]].append(entry)

        for code, entries in code_groups.items():
            if code.startswith('z'):
                continue
            if len(code) >= max_code_length:
                continue  # 加后缀会超长，跳过

            # 取去重后的候选顺序（按排序后的先后）
            # 每个 entry 格式: (code, tier, order, -freq, char)
            seen_entries = []
            seen_chars = set()
            for entry in entries:
                char = entry[4]
                if char not in seen_chars:
                    seen_entries.append(entry)
                    seen_chars.add(char)

            # 第2选 → code+z
            if len(seen_entries) >= 2:
                entry2 = seen_entries[1]
                char2 = entry2[4]
                if char2 in shortcut_leader_chars:
                    continue
                new_code_z = code + 'z'
                if (char2, new_code_z) not in used_text_code:
                    freq2 = char_freqs.get(char2, 0)
                    suffix_entries.append((new_code_z, 1, 0, -freq2, char2))
                    used_text_code.add((char2, new_code_z))
                    suffix_count += 1

    all_entries.extend(suffix_entries)
    all_entries.sort()
    print(f"后缀消重：生成 {suffix_count} 个 z 后缀条目")

    # ── 结构后缀消重 ──
    structure_suffix_entries = []
    structure_suffix_count = 0
    if suffix_structure:
        ids_structure = load_ids_structure_map()
        if len(suffix_structure_keymap) != 4 or not suffix_structure_keymap.isascii() or not suffix_structure_keymap.islower():
            raise ValueError("--suffix-structure-keymap 必须是 4 个小写 ASCII 字母")
        key_translate = dict(zip("asdf", suffix_structure_keymap))
        ids_structure = {
            char: key_translate.get(suffix_key, suffix_key)
            for char, suffix_key in ids_structure.items()
        }

        # 重建排序后的 code_groups
        code_groups_struct = defaultdict(list)
        for entry in all_entries:
            code_groups_struct[entry[0]].append(entry)

        occupied_codes = {entry[0] for entry in all_entries}
        protected_codes: set[str] = set()
        if suffix_structure_occupied_policy == "protect-min-score":
            for code, entries in code_groups_struct.items():
                first = entries[0]
                first_char = first[4]
                if first[1] < 5 or char_freqs.get(first_char, 0) >= suffix_structure_protect_min_score:
                    protected_codes.add(code)
        elif suffix_structure_occupied_policy != "skip-any":
            raise ValueError("--suffix-structure-occupied-policy 只能是 skip-any 或 protect-min-score")

        generated_structure_codes: set[str] = set()

        for code, entries_in_group in code_groups_struct.items():
            if code.startswith('z'):
                continue
            if len(code) >= max_code_length:
                continue

            seen_entries = []
            seen_chars = set()
            for entry in entries_in_group:
                char = entry[4]
                if char not in seen_chars:
                    seen_entries.append(entry)
                    seen_chars.add(char)

            # 为第2候选及之后的字生成结构后缀
            for entry in seen_entries[1:]:
                char = entry[4]
                if char in shortcut_leader_chars:
                    continue
                suffix_key = ids_structure.get(char)
                if suffix_key is None:
                    continue
                if not suffix_structure_charset_allows(char, suffix_structure_charset):
                    continue
                new_code = code + suffix_key
                # 结构后缀自身不互相制造新重码；对既有低频全码占用可按策略放行。
                if new_code in generated_structure_codes:
                    continue
                if suffix_structure_occupied_policy == "skip-any" and new_code in occupied_codes:
                    continue
                if suffix_structure_occupied_policy == "protect-min-score" and new_code in protected_codes:
                    continue
                if (char, new_code) in used_text_code:
                    continue
                freq = char_freqs.get(char, 0)
                structure_suffix_entries.append((new_code, 1, 0, -freq, char))
                used_text_code.add((char, new_code))
                occupied_codes.add(new_code)
                generated_structure_codes.add(new_code)
                structure_suffix_count += 1

        all_entries.extend(structure_suffix_entries)
        all_entries.sort()
        print(f"结构后缀消重：生成 {structure_suffix_count} 个结构后缀条目")

    # ── 第五步：写入文件 ──
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        dict_name = output_path.name.split('.')[0]
        header_lines = [
            "# encoding: utf-8",
            f"# 由 cangjie_builder.py 生成",
            "---",
            f"name: {dict_name}",
            f"version: '{_dt.date.today().isoformat()}'",
            "sort: by_weight",
        ]
        if vocabulary:
            header_lines.append(f"vocabulary: {vocabulary}")
        if max_phrase_length is not None:
            header_lines.append(f"max_phrase_length: {max_phrase_length}")
        if min_phrase_weight is not None:
            header_lines.append(f"min_phrase_weight: {min_phrase_weight}")
        header_lines.extend(["...", ""])
        f.write("\n".join(header_lines) + "\n")

        for code, tier, order, neg_freq, char in all_entries:
            f.write(f"{char}\t{code}\n")

    sc_count = len(shortcut_entries)
    fc_count = len(fullcode_entries)
    print(
        f"完成：简码={sc_count} 全码={fc_count}"
        f" z后缀={suffix_count} 结构后缀={structure_suffix_count}"
        f" 全码让位门槛={fullcode_yield_min_score:g}"
        f" 总计={len(all_entries)} 输出={output_path}"
    )


SCRIPT_DIR = Path(__file__).resolve().parent


HAN_RANGES: tuple[tuple[int, int], ...] = (
    (0x3400, 0x4DBF),   # 中日韩统一表意文字扩展 A
    (0x4E00, 0x9FFF),   # 中日韩统一表意文字
    (0xF900, 0xFAFF),   # 中日韩兼容表意文字
    (0x20000, 0x2A6DF), # 扩展 B
    (0x2A700, 0x2B739), # 扩展 C
    (0x2B740, 0x2B81D), # 扩展 D
    (0x2B820, 0x2CEA1), # 扩展 E
    (0x2CEB0, 0x2EBE0), # 扩展 F
    (0x2EBF0, 0x2EE5F), # 扩展 I
    (0x2F800, 0x2FA1F), # 中日韩兼容表意文字补充
    (0x30000, 0x3134A), # 扩展 G
    (0x31350, 0x323AF), # 扩展 H
)


@dataclass(frozen=True)
class Entry:
    text: str
    code: str


@dataclass(frozen=True)
class OutputEntry:
    text: str
    code: str
    original_code: str
    source_index: int
    weight: int


@dataclass(frozen=True)
class FrequencyEntry:
    text: str
    weight: int


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
        (0x3400 <= cp <= 0x4DBF) or    # CJK Unified Ideographs Extension A
        (0x20000 <= cp <= 0x2A6DF) or  # CJK Unified Ideographs Extension B
        (0x2A700 <= cp <= 0x2B73F) or  # CJK Unified Ideographs Extension C
        (0x2B740 <= cp <= 0x2B81F) or  # CJK Unified Ideographs Extension D
        (0x2B820 <= cp <= 0x2CEAF) or  # CJK Unified Ideographs Extension E
        (0x2CEB0 <= cp <= 0x2EBEF) or  # CJK Unified Ideographs Extension F
        (0x30000 <= cp <= 0x3134F) or  # CJK Unified Ideographs Extension G
        (0x31350 <= cp <= 0x323AF) or  # CJK Unified Ideographs Extension H
        (0x2EBF0 <= cp <= 0x2EE5F) or  # CJK Unified Ideographs Extension I
        (0x323B0 <= cp <= 0x3347F) or  # CJK Unified Ideographs Extension J
        (0xF900 <= cp <= 0xFAFF) or    # CJK Compatibility Ideographs
        (0x2F800 <= cp <= 0x2FA1F)     # CJK Compatibility Ideographs Supplement
    )


def is_common_han_char(text: str) -> bool:
    """判断是否为 Rime extended_charset 关闭时可见的常用汉字。"""
    if not is_han_char(text):
        return False
    return not is_extended_cjk(text)


def gb2312_level(text: str) -> int | None:
    """返回 GB2312 汉字级别：1=一级字，2=二级字，None=非 GB2312 汉字。"""
    if len(text) != 1 or not ('\u4e00' <= text <= '\u9fa5'):
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


def project_code(code: str, max_code_length: int) -> str:
    if len(code) <= max_code_length:
        return code
    return code[:max_code_length-1] + code[-1]


def build_fullcode_yield_order(
    entries: list[tuple[str, str, int]],
    shortcut_chars: set[str],
    min_promote_score: float = DEFAULT_FULLCODE_YIELD_MIN_SCORE,
) -> dict[tuple[str, str], int]:
    """计算全码候选位次：有简码的首选让位给未获简码的常用字。

    `entries` 元素为 (char, code, freq)。同码组先按字频降序排列；
    如果首选字已有 S1/S2/S3/S4 简码，则把后面第一个没有简码且字频
    达到 `min_promote_score` 的字提到首位。找不到这样的字就不动。
    """

    code_groups: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    for entry in entries:
        code_groups[entry[1]].append(entry)

    order: dict[tuple[str, str], int] = {}
    for group in code_groups.values():
        yielded = sorted(group, key=lambda entry: (-entry[2], entry[0]))
        if yielded and yielded[0][0] in shortcut_chars:
            promoted_idx = -1
            for index, entry in enumerate(yielded[1:], start=1):
                if entry[0] not in shortcut_chars and entry[2] >= min_promote_score:
                    promoted_idx = index
                    break
            if promoted_idx > 0:
                promoted = yielded.pop(promoted_idx)
                yielded.insert(0, promoted)

        for rank, (char, code, _) in enumerate(yielded):
            order[(char, code)] = rank
    return order


def build_shortcut_leader_chars(entries: list[tuple[str, int, int, int, str]]) -> set[str]:
    """返回已经拥有首选简码入口的字。

    后缀 `z` 是给第二候选补直达路。如果某字已经在任一简码位是
    第一候选，再给它补第二候选后缀就是冗余路径。
    """

    leaders: set[str] = set()
    code_groups: dict[str, list[tuple[str, int, int, int, str]]] = defaultdict(list)
    for entry in entries:
        code_groups[entry[0]].append(entry)

    for group in code_groups.values():
        first = group[0]
        if first[1] < 5:
            leaders.add(first[4])
    return leaders


def parse_cangjie_dict(path: Path) -> list[Entry]:
    lines = path.read_text(encoding="utf-8").splitlines()
    in_body = False
    entries: list[Entry] = []

    for lineno, line in enumerate(lines, start=1):
        if line.strip() == "...":
            in_body = True
            continue
        if not in_body:
            continue
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        text, code = parts[0], parts[1]
        if not text or not code:
            continue

        if not code.isascii() or not code.islower():
            raise ValueError(f"{path}:{lineno}: 遇到异常编码 {code!r}")

        entries.append(Entry(text=text, code=code))

    return entries


def parse_frequency_file(path: Path) -> tuple[dict[str, int], list[FrequencyEntry]]:
    """读取 essay-zh-hans.txt，提取单字频率和词语频率。"""
    char_frequencies: dict[str, int] = {}
    phrase_frequencies: dict[str, int] = {}

    if not path.is_file():
        return char_frequencies, []

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        text, weight_text = parts[0], parts[1]

        try:
            weight = int(weight_text)
        except ValueError as exc:
            raise ValueError(f"{path}:{lineno}: 遇到异常词频 {weight_text!r}") from exc

        if is_han_char(text):
            if weight > char_frequencies.get(text, -1):
                char_frequencies[text] = weight
        elif len(text) > 1 and is_han_text(text):
            if weight > phrase_frequencies.get(text, -1):
                phrase_frequencies[text] = weight

    phrases = [
        FrequencyEntry(text=text, weight=weight)
        for text, weight in phrase_frequencies.items()
    ]
    return char_frequencies, phrases


def get_weighted_frequencies() -> dict[str, int]:
    """计算多份语料库的加权得分并返回合并后的字典。"""
    char_scores = defaultdict(int)
    for name, path in FREQ_PATHS.items():
        if path.exists():
            weight = FREQ_WEIGHTS.get(name, 1)
            freqs, _ = parse_frequency_file(path)
            for char, val in freqs.items():
                char_scores[char] += val * weight
        else:
            print(f"Warning: Frequency file not found: {path}", file=sys.stderr)
    return char_scores


def load_ids_structure_map(ids_path: Path = None) -> dict[str, str]:
    """从 ids.txt 加载汉字结构映射：char -> suffix_key (a/s/d/f)。

    键位固定为 asdf（全左手）：
      a = 左右/左中右  s = 上下/上中下  d = 包围/半包围  f = 独体
    """
    if ids_path is None:
        ids_path = IDS_PATH
    mapping: dict[str, str] = {}
    if not ids_path.exists():
        print(f"Warning: IDS file not found: {ids_path}", file=sys.stderr)
        return mapping
    with open(ids_path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 3:
                continue
            char = parts[1]
            ids = parts[2]
            if len(char) != 1:
                continue
            first = ids[0] if ids else ""
            if first in _LR:
                mapping[char] = "a"
            elif first in _UD:
                mapping[char] = "s"
            elif first in _WRAP:
                mapping[char] = "d"
            else:
                mapping[char] = "f"
    print(f"IDS 结构数据已加载：{len(mapping)} 字")
    return mapping


def normalize_prefixes(prefixes: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for item in prefixes:
        for part in item.split(","):
            part = part.strip()
            if part:
                normalized.append(part)
    return tuple(dict.fromkeys(normalized))


def display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_output(
    entries: list[Entry],
    *,
    name: str,
    version: str,
    sort: str,
    vocabulary: str | None,
    max_phrase_length: int,
    min_phrase_weight: int,
    generated_phrase_min_weight: int,
    include_phrases: bool,
    only_han: bool,
    excluded_prefixes: tuple[str, ...],
    source_path: Path,
    frequency_path: Path,
    frequencies: dict[str, int],
    phrases: list[FrequencyEntry],
    max_code_length: int,
    script_name: str,
) -> tuple[str, Counter]:
    stats: Counter = Counter()
    emitted: set[tuple[str, str]] = set()
    output_entries: list[OutputEntry] = []
    char_codes: dict[str, str] = {}

    for source_index, entry in enumerate(entries):
        stats["seen"] += 1

        if excluded_prefixes and entry.code.startswith(excluded_prefixes):
            stats["dropped_by_prefix"] += 1
            continue

        if only_han and not is_han_char(entry.text):
            stats["dropped_non_han"] += 1
            continue

        new_code = project_code(entry.code, max_code_length)
        item = (entry.text, new_code)
        if item in emitted:
            stats["dropped_duplicate"] += 1
            continue

        emitted.add(item)
        output_entries.append(
            OutputEntry(
                text=entry.text,
                code=new_code,
                original_code=entry.code,
                source_index=source_index,
                weight=frequencies.get(entry.text, 0),
            )
        )
        char_codes.setdefault(entry.text, new_code)
        stats["kept"] += 1

    if include_phrases:
        phrase_source_base = len(entries)
        for phrase_index, phrase in enumerate(phrases):
            stats["phrase_seen"] += 1

            if len(phrase.text) > max_phrase_length:
                stats["phrase_dropped_by_length"] += 1
                continue

            if phrase.weight < generated_phrase_min_weight:
                stats["phrase_dropped_by_weight"] += 1
                continue

            code_parts: list[str] = []
            for char in phrase.text:
                char_code = char_codes.get(char)
                if not char_code:
                    stats["phrase_dropped_by_missing_code"] += 1
                    break
                code_parts.append(char_code)
            else:
                phrase_code = "".join(code_parts)
                item = (phrase.text, phrase_code)
                if item in emitted:
                    stats["phrase_dropped_duplicate"] += 1
                    continue

                emitted.add(item)
                output_entries.append(
                    OutputEntry(
                        text=phrase.text,
                        code=phrase_code,
                        original_code=phrase_code,
                        source_index=phrase_source_base + phrase_index,
                        weight=phrase.weight,
                    )
                )
                stats["phrase_kept"] += 1

    output_entries.sort(
        key=lambda item: (
            item.code,
            -item.weight,
            item.original_code,
            item.source_index,
        )
    )
    body_lines = [f"{entry.text}\t{entry.code}" for entry in output_entries]

    header = [
        "# encoding: utf-8",
        "#",
        f"# 由 scripts/{script_name} 生成",
        f"# 来源：{display_path(source_path)}",
        f"# 词频排序：{display_path(frequency_path)}",
        f"# 规则：1 至 {max_code_length} 码保留原码；{max_code_length + 1} 码及以上取" + 
        ("首码、次码、末码" if max_code_length == 3 else "第一二三末码"),
        f"# 排序：先按{'三' if max_code_length == 3 else '四'}码编码分组；同码内按单字词频降序排列",
    ]
    if include_phrases:
        header.append(f"# 词语：由词频文件逐字取{'三' if max_code_length == 3 else '四'}码并拼接生成")
    header.extend(
        [
            "#",
            "---",
            f"name: {name}",
            f"version: '{version}'",
            f"sort: {sort}",
        ]
    )
    if vocabulary:
        header.append(f"vocabulary: {vocabulary}")
    if max_phrase_length is not None:
        header.append(f"max_phrase_length: {max_phrase_length}")
    if vocabulary:
        header.append(f"min_phrase_weight: {min_phrase_weight}")
    header.extend(["...", ""])
    return "\n".join(header + body_lines) + "\n", stats


def run_generator(
    description: str,
    default_output: str,
    default_name: str,
    default_frequency_file: str,
    max_code_length: int,
    script_name: str,
    default_sort: str = "by_weight",
    default_no_vocabulary: bool = False,
    default_max_phrase_length: int = 7,
) -> int:
    parser = argparse.ArgumentParser(
        description=description,
        usage="%(prog)s [选项]",
        add_help=False,
    )
    parser._optionals.title = "选项"
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="显示帮助信息并退出",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=REPO_ROOT / "schemas/cangjie/cangjie5/cangjie5.dict.yaml",
        help="源仓颉五代码表",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / default_output,
        help="输出字典路径；填 - 表示输出到标准输出",
    )
    parser.add_argument(
        "--name",
        default=default_name,
        help="写入 YAML 头部的字典名称",
    )
    parser.add_argument(
        "--vocabulary",
        default="essay-zh-hans",
        help="主字典使用的词频文件名称",
    )
    parser.add_argument(
        "--no-vocabulary",
        action="store_true",
        default=default_no_vocabulary,
        help="不写入 vocabulary、min_phrase_weight 字段",
    )
    parser.add_argument(
        "--frequency-file",
        type=Path,
        default=REPO_ROOT / default_frequency_file,
        help="用于排序单字候选的词频文件；找不到时所有单字按 0 频处理",
    )
    parser.add_argument(
        "--include-phrases",
        action="store_true",
        help=f"根据词频文件生成多字词条；词语编码为每个字的{'三' if max_code_length == 3 else '四'}码直接拼接",
    )
    parser.add_argument(
        "--generated-phrase-min-weight",
        type=int,
        default=1,
        help="生成多字词条时使用的最低词频；不影响 YAML min_phrase_weight 字段",
    )
    parser.add_argument(
        "--version",
        default=_dt.date.today().isoformat(),
        help="写入 YAML 头部的字典版本",
    )
    parser.add_argument(
        "--sort",
        default=default_sort,
        help="YAML sort 字段",
    )
    parser.add_argument(
        "--max-phrase-length",
        type=int,
        default=default_max_phrase_length,
        help="YAML max_phrase_length 字段",
    )
    parser.add_argument(
        "--min-phrase-weight",
        type=int,
        default=100,
        help="YAML min_phrase_weight 字段",
    )
    parser.add_argument(
        "--keep-non-han",
        action="store_true",
        help="保留标点等非汉字条目",
    )
    parser.add_argument(
        "--no-default-excluded-prefixes",
        action="store_true",
        help='不使用默认的 "z" 前缀过滤',
    )
    parser.add_argument(
        "--exclude-code-prefix",
        action="append",
        default=[],
        help="额外过滤的编码前缀；可重复传入，例如 --exclude-code-prefix z --exclude-code-prefix zx",
    )
    
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"找不到源文件：{args.source}", file=sys.stderr)
        return 2

    prefixes = []
    if not args.no_default_excluded_prefixes:
        prefixes.append("z")
    prefixes.extend(args.exclude_code_prefix)
    excluded_prefixes = normalize_prefixes(prefixes)

    entries = parse_cangjie_dict(args.source)
    frequencies, phrases = parse_frequency_file(args.frequency_file)
    output_text, stats = build_output(
        entries,
        name=args.name,
        version=args.version,
        sort=args.sort,
        vocabulary=None if args.no_vocabulary else args.vocabulary,
        max_phrase_length=args.max_phrase_length,
        min_phrase_weight=args.min_phrase_weight,
        generated_phrase_min_weight=args.generated_phrase_min_weight,
        include_phrases=args.include_phrases,
        only_han=not args.keep_non_han,
        excluded_prefixes=excluded_prefixes,
        source_path=args.source,
        frequency_path=args.frequency_file,
        frequencies=frequencies,
        phrases=phrases,
        max_code_length=max_code_length,
        script_name=script_name,
    )

    if str(args.output) == "-":
        sys.stdout.write(output_text)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp_output = args.output.with_name(args.output.name + ".tmp")
        with temp_output.open("w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(output_text)
        temp_output.replace(args.output)

    print(
        "完成："
        f" 读入={stats['seen']}"
        f" 保留={stats['kept']}"
        f" 按前缀过滤={stats['dropped_by_prefix']}"
        f" 非汉字过滤={stats['dropped_non_han']}"
        f" 重复过滤={stats['dropped_duplicate']}"
        f" 词语保留={stats['phrase_kept']}"
        f" 输出={args.output}",
        file=sys.stderr,
    )
    if excluded_prefixes:
        print(f"过滤前缀：{', '.join(excluded_prefixes)}", file=sys.stderr)
    print(
        f"词频文件：{args.frequency_file}"
        f" 单字={len(frequencies)}"
        f" 词语={len(phrases)}"
        f" 生成词语={'是' if args.include_phrases else '否'}",
        file=sys.stderr,
    )
    if args.include_phrases:
        print(
            "词语过滤："
            f" 超长={stats['phrase_dropped_by_length']}"
            f" 低频<{args.generated_phrase_min_weight}={stats['phrase_dropped_by_weight']}"
            f" 缺字码={stats['phrase_dropped_by_missing_code']}"
            f" 重复={stats['phrase_dropped_duplicate']}",
            file=sys.stderr,
        )
    print(
        f"仅保留汉字={'否' if args.keep_non_han else '是'}"
        f" 词语模型={'无' if args.no_vocabulary else args.vocabulary}",
        file=sys.stderr,
    )
    return 0
