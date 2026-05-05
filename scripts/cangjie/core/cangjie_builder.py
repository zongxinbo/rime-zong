#!/usr/bin/env python3
"""核心模块：从仓颉五代码表按指定长度规则（三码、四码等）取码生成字典。"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

# ... (keep existing definitions: HAN_RANGES, Entry, etc.)

def generate_dict(
    output_path: Path,
    shortcut_paths: dict,
    source_dict: Path,
    freq_file: Path,
    max_code_length: int = 5,
    exclude_extended: bool = False,
    vocabulary: str = None,
    max_phrase_length: int = None,
    min_phrase_weight: int = None,
):
    """生成最终字典。

    支持 Z/S1/S2/S3/S4 简码层级，并实现"位置降权"：
    同码组内，已获简码的字的长全码条目排在最后（退避），
    保证首选候选是真正需要该编码的字。
    """
    print(f"正在解析原始仓颉编码: {source_dict}...")
    raw_entries = parse_cangjie_dict(source_dict)
    char_full_codes = defaultdict(list)
    for e in raw_entries:
        if (is_common_han_char(e.text) if exclude_extended else is_han_char(e.text)) and not (e.code.startswith('z') or e.code.startswith('x')):
            char_full_codes[e.text].append(e.code)

    # ── 第一步：加载各层级简码 ──
    print("正在加载简码规则...")
    shortcut_entries = []  # (char, code, priority)
    chars_with_shortcut = {}  # char -> 最短简码长度

    def load_shortcut(path, priority):
        if not path or not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) == 2 and not parts[0].startswith("#"):
                    char, code = parts[0], parts[1]
                    shortcut_entries.append((char, code, priority))
                    # 记录该字获得的最短简码长度
                    cur = chars_with_shortcut.get(char, 999)
                    if len(code) < cur:
                        chars_with_shortcut[char] = len(code)

    # 优先级数字越小越靠前
    load_shortcut(shortcut_paths.get('z'), 0)
    load_shortcut(shortcut_paths.get(1), 1)
    load_shortcut(shortcut_paths.get(2), 2)
    load_shortcut(shortcut_paths.get(3), 3)
    load_shortcut(shortcut_paths.get(4), 4)

    # ── 第二步：生成全码条目 ──
    print("正在生成单字...")
    char_freqs, _ = parse_frequency_file(freq_file)

    used_text_code = set()
    for char, code, _ in shortcut_entries:
        used_text_code.add((char, code))

    fullcode_entries = []  # (char, code, freq, is_demoted)
    for char, full_codes in char_full_codes.items():
        freq = char_freqs.get(char, 0)
        shortcut_len = chars_with_shortcut.get(char, 999)
        for full_code in full_codes:
            code_proj = project_code(full_code, max_code_length)
            if (char, code_proj) in used_text_code:
                continue
            used_text_code.add((char, code_proj))
            # 位置降权：如果该字已有更短的简码，则标记退避
            is_demoted = len(code_proj) > shortcut_len
            fullcode_entries.append((char, code_proj, freq, is_demoted))

    # ── 第三步：合并排序输出 ──
    # 排序键设计：
    #   1. 按编码分组
    #   2. 简码条目优先（priority 0-4），然后原生全码（非退避），最后退避条目
    #   3. 同级内按字频降序
    all_entries = []

    for char, code, priority in shortcut_entries:
        freq = char_freqs.get(char, 0)
        # sort_tier: 简码 (0-4) < 原生全码 (5) < 退避 (6)
        all_entries.append((code, priority, -freq, char))

    for char, code, freq, is_demoted in fullcode_entries:
        tier = 6 if is_demoted else 5
        all_entries.append((code, tier, -freq, char))

    all_entries.sort()

    # ── 第四步：写入文件 ──
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

        for code, tier, neg_freq, char in all_entries:
            f.write(f"{char}\t{code}\n")

    sc_count = len(shortcut_entries)
    fc_count = len(fullcode_entries)
    dm_count = sum(1 for _, _, _, d in fullcode_entries if d)
    print(
        f"完成：简码={sc_count} 全码={fc_count} 退避={dm_count}"
        f" 总计={len(all_entries)} 输出={output_path}"
    )


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent


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


def is_common_han_char(text: str) -> bool:
    """判断是否为常用汉字（Rime 默认字符集，即基本多文种平面 BMP 内的汉字，排除 Ext-B 及以上的增广生僻字）"""
    if not is_han_char(text):
        return False
    return ord(text) < 0x20000


def is_han_text(text: str) -> bool:
    return bool(text) and all(is_han_char(char) for char in text)


def project_code(code: str, max_code_length: int) -> str:
    if len(code) <= max_code_length:
        return code
    return code[:max_code_length-1] + code[-1]


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
