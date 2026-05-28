from __future__ import annotations

import argparse
import datetime as _dt
import sys
from collections import Counter
from pathlib import Path

from .charset import is_han_char
from .code_utils import project_code
from .frequency import parse_frequency_file
from .io import display_path, normalize_prefixes, parse_cangjie_dict
from .models import Entry, FrequencyEntry, OutputEntry
from .paths import CANGJIE5_DICT_PATH, REPO_ROOT


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
        f"# 规则：1 至 {max_code_length} 码保留原码；{max_code_length + 1} 码及以上取"
        + ("首码、次码、末码" if max_code_length == 3 else "第一二三末码"),
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
    default_output: str | Path,
    default_name: str,
    default_frequency_file: str | Path,
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
    parser.add_argument("-h", "--help", action="help", help="显示帮助信息并退出")
    parser.add_argument(
        "--source",
        type=Path,
        default=CANGJIE5_DICT_PATH,
        help="源仓颉五代码表",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / default_output,
        help="输出字典路径；填 - 表示输出到标准输出",
    )
    parser.add_argument("--name", default=default_name, help="写入 YAML 头部的字典名称")
    parser.add_argument("--vocabulary", default="essay-zh-hans", help="主字典使用的词频文件名称")
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
    parser.add_argument("--version", default=_dt.date.today().isoformat(), help="写入 YAML 头部的字典版本")
    parser.add_argument("--sort", default=default_sort, help="YAML sort 字段")
    parser.add_argument("--max-phrase-length", type=int, default=default_max_phrase_length, help="YAML max_phrase_length 字段")
    parser.add_argument("--min-phrase-weight", type=int, default=100, help="YAML min_phrase_weight 字段")
    parser.add_argument("--keep-non-han", action="store_true", help="保留标点等非汉字条目")
    parser.add_argument("--no-default-excluded-prefixes", action="store_true", help='不使用默认的 "z" 前缀过滤')
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
