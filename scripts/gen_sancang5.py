#!/usr/bin/env python3
"""从仓颉五代码表生成投影版三码字典。

默认投影规则：
- 1 至 3 码字：保留原码
- 4 码及以上：取首码、次码、末码

默认过滤规则：
- 丢弃编码以 ``z`` 开头的条目
- 只保留单个汉字条目

这意味着：
- 兼容汉字、部首、笔画、符号等 ``z*`` 条目默认会被过滤
- ``卞	yy``、``齊	yx`` 这类真汉字会保留
- ``「	yyyaa`` 这类标点符号会通过“只保留汉字”规则过滤，
  不靠容易误伤的 ``yy*`` 前缀黑名单
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent


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


def is_han_text(text: str) -> bool:
    return bool(text) and all(is_han_char(char) for char in text)


def project_code(code: str) -> str:
    if len(code) <= 3:
        return code
    return code[0] + code[1] + code[-1]


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

        new_code = project_code(entry.code)
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
        "# 由 scripts/gen_sancang5.py 生成",
        f"# 来源：{display_path(source_path)}",
        f"# 词频排序：{display_path(frequency_path)}",
        "# 规则：1 至 3 码保留原码；4 码及以上取首码、次码、末码",
        "# 排序：先按三码编码分组；同码内按单字词频降序排列",
    ]
    if include_phrases:
        header.append("# 词语：由词频文件逐字取三码并拼接生成")
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
        header.extend(
            [
                f"vocabulary: {vocabulary}",
                f"max_phrase_length: {max_phrase_length}",
                f"min_phrase_weight: {min_phrase_weight}",
            ]
        )
    header.extend(["...", ""])
    return "\n".join(header + body_lines) + "\n", stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="把仓颉五代单字编码投影成三码字典。",
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
        default=REPO_ROOT / "cangjie5/cangjie5.dict.yaml",
        help="源仓颉五代码表",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "sancang5/sancang5.dict.yaml",
        help="输出字典路径；填 - 表示输出到标准输出",
    )
    parser.add_argument(
        "--name",
        default="sancang5",
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
        help="不写入 vocabulary、max_phrase_length、min_phrase_weight 字段",
    )
    parser.add_argument(
        "--frequency-file",
        type=Path,
        default=REPO_ROOT / "sancang5/essay-zh-hans.txt",
        help="用于排序单字候选的词频文件；找不到时所有单字按 0 频处理",
    )
    parser.add_argument(
        "--include-phrases",
        action="store_true",
        help="根据词频文件生成多字词条；词语编码为每个字的三码直接拼接",
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
        default="by_weight",
        help="YAML sort 字段",
    )
    parser.add_argument(
        "--max-phrase-length",
        type=int,
        default=7,
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()

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


if __name__ == "__main__":
    raise SystemExit(main())
