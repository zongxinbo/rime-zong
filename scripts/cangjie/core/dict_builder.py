from __future__ import annotations

import datetime as _dt
from collections import defaultdict
from pathlib import Path

from .charset import is_common_han_char, is_han_char, suffix_structure_charset_allows
from .code_utils import build_fullcode_yield_order, build_shortcut_leader_chars, project_code
from .dedup import build_dedup_prefix_entries, build_z_suffix_entries, unique_seen_entries
from .frequency import parse_frequency_file
from .glyph_codes import get_glyph_preferred_codes
from .ids import load_ids_structure_map
from .io import parse_cangjie_dict
from .paths import (
    DEFAULT_FULLCODE_YIELD_MIN_SCORE,
    PREFIX_CODE_2_PATH,
    PREFIX_CODE_3_PATH,
    PREFIX_CODE_4_SICANG5_PATH,
    PREFIX_CODE_4_WUCANG5_PATH,
    PREFIX_CODE_5_WUCANG5_PATH,
)


def load_shortcut_entries(shortcut_paths: dict) -> tuple[list[tuple[str, str, int | float]], set[str]]:
    """加载字根码和 S1/S2/S3/S4 简码原型。"""
    shortcut_entries: list[tuple[str, str, int | float]] = []
    root_chars: set[str] = set()

    def load_shortcut(path: Path | None, priority: int | float) -> None:
        if not path or not path.exists():
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) == 2 and not parts[0].startswith("#"):
                    char, code = parts[0], parts[1]
                    shortcut_entries.append((char, code, priority))
                    if priority == 0:
                        root_chars.add(char)

    load_shortcut(shortcut_paths.get("root"), 0)
    load_shortcut(shortcut_paths.get(1), 1)
    load_shortcut(shortcut_paths.get("fixed_prefix"), 1.5)
    load_shortcut(shortcut_paths.get(2), 2)
    load_shortcut(shortcut_paths.get(3), 3)
    load_shortcut(shortcut_paths.get(4), 4)
    return shortcut_entries, root_chars


def collect_char_full_codes(
    source_dict: Path,
    *,
    exclude_extended: bool,
    only_first_full_code: bool,
) -> dict[str, list[str]]:
    raw_entries = parse_cangjie_dict(source_dict)
    char_full_codes: dict[str, list[str]] = defaultdict(list)
    for entry in raw_entries:
        is_allowed = is_common_han_char(entry.text) if exclude_extended else is_han_char(entry.text)
        if is_allowed and not (entry.code.startswith("z") or entry.code.startswith("x")):
            if only_first_full_code and entry.text in char_full_codes:
                continue
            char_full_codes[entry.text].append(entry.code)
    return char_full_codes


def build_fullcode_entries(
    char_full_codes: dict[str, list[str]],
    *,
    root_chars: set[str],
    used_text_code: set[tuple[str, str]],
    char_freqs: dict[str, int],
    max_code_length: int,
) -> list[tuple[str, str, int]]:
    fullcode_entries: list[tuple[str, str, int]] = []
    for char, full_codes in char_full_codes.items():
        if char in root_chars:
            full_codes = [code for code in full_codes if len(code) != 1]
        freq = char_freqs.get(char, 0)
        for full_code in full_codes:
            code_proj = project_code(full_code, max_code_length)
            if (char, code_proj) in used_text_code:
                continue
            used_text_code.add((char, code_proj))
            fullcode_entries.append((char, code_proj, freq))
    return fullcode_entries


def build_base_entries(
    shortcut_entries: list[tuple[str, str, int | float]],
    fullcode_entries: list[tuple[str, str, int]],
    *,
    char_freqs: dict[str, int],
    fullcode_yield: bool,
    fullcode_yield_min_score: float,
) -> list[tuple[str, int | float, int, int, str]]:
    all_entries: list[tuple[str, int, int, int, str]] = []
    fullcode_order = build_fullcode_yield_order(
        fullcode_entries,
        shortcut_entries if fullcode_yield else [],
        min_promote_score=fullcode_yield_min_score,
    )

    for char, code, priority in shortcut_entries:
        freq = char_freqs.get(char, 0)
        all_entries.append((code, priority, 0, -freq, char))

    for char, code, freq in fullcode_entries:
        all_entries.append((code, 5, fullcode_order[(char, code)], -freq, char))

    all_entries.sort()
    return all_entries


def build_structure_suffix_entries(
    all_entries: list[tuple[str, int, int, int, str]],
    *,
    occupied_entries: list[tuple[str, int, int, int, str]] | None = None,
    used_text_code: set[tuple[str, str]],
    shortcut_leader_chars: set[str],
    char_freqs: dict[str, int],
    max_code_length: int,
    suffix_structure_charset: str,
    suffix_structure_occupied_policy: str,
    suffix_structure_protect_min_score: float,
    suffix_structure_keymap: str,
) -> list[tuple[str, int, int, int, str]]:
    ids_structure = load_ids_structure_map()
    if len(suffix_structure_keymap) != 4 or not suffix_structure_keymap.isascii() or not suffix_structure_keymap.islower():
        raise ValueError("--suffix-structure-keymap 必须是 4 个小写 ASCII 字母")
    key_translate = dict(zip("asdf", suffix_structure_keymap))
    ids_structure = {
        char: key_translate.get(suffix_key, suffix_key)
        for char, suffix_key in ids_structure.items()
    }

    code_groups_struct: dict[str, list[tuple[str, int, int, int, str]]] = defaultdict(list)
    for entry in all_entries:
        code_groups_struct[entry[0]].append(entry)

    occupied_source = all_entries if occupied_entries is None else occupied_entries
    occupied_codes = {entry[0] for entry in occupied_source}
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
    structure_suffix_entries: list[tuple[str, int, int, int, str]] = []

    for code, entries_in_group in code_groups_struct.items():
        if code.startswith(("z", "x")):
            continue
        if len(code) >= max_code_length:
            continue

        seen_entries = unique_seen_entries(entries_in_group)
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

    return structure_suffix_entries


def write_final_dict(
    output_path: Path,
    all_entries: list[tuple[str, int, int, int, str]],
    *,
    vocabulary: str | None,
    max_phrase_length: int | None,
    min_phrase_weight: int | None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        dict_name = output_path.name.split(".")[0]
        header_lines = [
            "# encoding: utf-8",
            "# 由 cangjie_builder.py 生成",
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


def write_prefix_prototypes(
    prefix_entries: list[tuple[int, tuple[str, int | float, int, int, str]]],
    paths: dict[int, Path],
) -> dict[int, int]:
    """写出自动 z/x 前缀码审阅文件。"""
    grouped: dict[int, list[tuple[str, int | float, int, int, str]]] = defaultdict(list)
    for level, entry in prefix_entries:
        if level in paths:
            grouped[level].append(entry)

    counts: dict[int, int] = {}
    for level, path in paths.items():
        entries = sorted(grouped.get(level, []))
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# 自动 z/x 前缀 {level} 码审阅文件；构建时覆盖生成"]
        for code, _, _, _, char in entries:
            lines.append(f"{char}\t{code}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        counts[level] = len(entries)
    return counts


def write_code_prototype(
    entries: list[tuple[str, int | float, int, int, str]],
    path: Path,
    *,
    title: str,
) -> int:
    """写出自动码表审阅文件，两列：字、码。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(entries)
    lines = [f"# {title}；构建时覆盖生成"]
    for code, _, _, _, char in rows:
        lines.append(f"{char}\t{code}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(rows)


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
    fullcode_yield: bool = True,
    fullcode_yield_min_score: float = DEFAULT_FULLCODE_YIELD_MIN_SCORE,
    suffix_z: bool = True,
    suffix_z_charset: str = "all",
    suffix_z_min_score: float = 0,
    suffix_z_rank_suffixes: tuple[tuple[int, str], ...] = ((2, "z"),),
    suffix_z_max_source_length: int | None = None,
    suffix_z_occupied_policy: str = "strict",
    suffix_code_path: Path | None = None,
    dedup_prefix: bool = True,
    dedup_prefix_charset: str = "frequency",
    dedup_prefix_min_score: float = 1,
    dedup_prefix_short: bool = True,
    dedup_prefix_full: bool = True,
    dedup_prefix_short_levels: tuple[int, ...] = (2, 3),
    dedup_prefix_full_source_length: int = 4,
    dedup_prefix_deep_rank_multiplier: float = 1.5,
    dedup_prefix_source_max_code_length: int | None = 4,
    dedup_prefix_scheme: str | None = None,
    dedup_prefix_scheme_short_levels: tuple[int, ...] = (),
    dedup_prefix_scheme_full_source_length: int | None = None,
    dedup_prefix_short_level_char_freqs: dict[int, dict[str, int]] | None = None,
    dedup_prefix_full_char_freqs: dict[str, int] | None = None,
    suffix_structure: bool = False,
    suffix_structure_charset: str = "gbk",
    suffix_structure_occupied_policy: str = "protect-min-score",
    suffix_structure_protect_min_score: float = 100000,
    suffix_structure_keymap: str = "zxwa",
    weights: str | None = None,
):
    """生成最终字典。"""
    print(f"正在解析原始仓颉编码: {source_dict}...")
    char_full_codes = collect_char_full_codes(
        source_dict,
        exclude_extended=exclude_extended,
        only_first_full_code=only_first_full_code,
    )

    print("正在加载简码规则...")
    shortcut_entries, root_chars = load_shortcut_entries(shortcut_paths)

    print("正在生成单字...")
    if char_freqs is None:
        char_freqs, _ = parse_frequency_file(freq_file)
    else:
        print("使用预加载的加权字频数据进行排序...")

    used_text_code = {(char, code) for char, code, _ in shortcut_entries}
    fullcode_entries = build_fullcode_entries(
        char_full_codes,
        root_chars=root_chars,
        used_text_code=used_text_code,
        char_freqs=char_freqs,
        max_code_length=max_code_length,
    )
    all_entries = build_base_entries(
        shortcut_entries,
        fullcode_entries,
        char_freqs=char_freqs,
        fullcode_yield=fullcode_yield,
        fullcode_yield_min_score=fullcode_yield_min_score,
    )
    shortcut_leader_chars = build_shortcut_leader_chars(all_entries)
    shortcut_source_entries = list(all_entries)
    if weights is not None:
        preferred_codes = {
            text: project_code(code, max_code_length)
            for text, code in get_glyph_preferred_codes(weights).items()
        }
        shortcut_source_entries = [
            entry
            for entry in all_entries
            if entry[1] < 5
            or entry[4] not in preferred_codes
            or entry[0] == preferred_codes[entry[4]]
        ]

    natural_shortcut_source_entries = list(shortcut_source_entries)
    natural_shortcut_leader_chars = set(shortcut_leader_chars)

    z_suffix_count = 0
    dedup_prefix_count = 0
    prefix_counts: dict[int, int] = {}
    if dedup_prefix:
        def build_prefix_source(source_max_code_length: int | None):
            if source_max_code_length is None:
                return shortcut_source_entries, build_shortcut_leader_chars(all_entries)

            prefix_used_text_code = {(char, code) for char, code, _ in shortcut_entries}
            prefix_fullcode_entries = build_fullcode_entries(
                char_full_codes,
                root_chars=root_chars,
                used_text_code=prefix_used_text_code,
                char_freqs=char_freqs,
                max_code_length=source_max_code_length,
            )
            prefix_all_entries = build_base_entries(
                shortcut_entries,
                prefix_fullcode_entries,
                char_freqs=char_freqs,
                fullcode_yield=fullcode_yield,
                fullcode_yield_min_score=fullcode_yield_min_score,
            )
            prefix_source_entries = prefix_all_entries
            if weights is not None:
                preferred_prefix_codes = {
                    text: project_code(code, source_max_code_length)
                    for text, code in get_glyph_preferred_codes(weights).items()
                }
                prefix_source_entries = [
                    entry
                    for entry in prefix_all_entries
                    if entry[1] < 5
                    or entry[4] not in preferred_prefix_codes
                    or entry[0] == preferred_prefix_codes[entry[4]]
                ]
            return prefix_source_entries, build_shortcut_leader_chars(prefix_all_entries)

        def append_prefix_entries(entries_with_levels: list[tuple[int, tuple[str, int | float, int, int, str]]]) -> None:
            nonlocal dedup_prefix_count, shortcut_leader_chars
            entries = [entry for _, entry in entries_with_levels]
            dedup_prefix_count += len(entries)
            all_entries.extend(entries)
            all_entries.sort()
            shortcut_source_entries.extend(entries)
            shortcut_source_entries.sort()
            shortcut_leader_chars = build_shortcut_leader_chars(all_entries)

        shared_entries_with_levels: list[tuple[int, tuple[str, int | float, int, int, str]]] = []
        if dedup_prefix_short:
            shared_source_entries, shared_leader_chars = build_prefix_source(dedup_prefix_source_max_code_length)
            shared_entries_with_levels = build_dedup_prefix_entries(
                shared_source_entries,
                occupied_entries=shared_source_entries,
                used_text_code=used_text_code,
                shortcut_leader_chars=shared_leader_chars,
                char_freqs=char_freqs,
                short_level_char_freqs=dedup_prefix_short_level_char_freqs,
                full_char_freqs=dedup_prefix_full_char_freqs,
                max_code_length=dedup_prefix_source_max_code_length or max_code_length,
                charset=dedup_prefix_charset,
                min_score=dedup_prefix_min_score,
                short=True,
                full=False,
                short_levels=dedup_prefix_short_levels,
                full_source_length=dedup_prefix_full_source_length,
                deep_rank_multiplier=dedup_prefix_deep_rank_multiplier,
            )
            prefix_counts.update(write_prefix_prototypes(
                shared_entries_with_levels,
                {
                    2: PREFIX_CODE_2_PATH,
                    3: PREFIX_CODE_3_PATH,
                },
            ))
            append_prefix_entries(shared_entries_with_levels)

        scheme_entries_with_levels: list[tuple[int, tuple[str, int | float, int, int, str]]] = []
        if dedup_prefix_scheme == "sicang5":
            scheme_source_entries = shortcut_source_entries
            scheme_entries_with_levels = build_dedup_prefix_entries(
                scheme_source_entries,
                occupied_entries=scheme_source_entries,
                used_text_code=used_text_code,
                shortcut_leader_chars=shortcut_leader_chars,
                char_freqs=char_freqs,
                short_level_char_freqs=dedup_prefix_short_level_char_freqs,
                full_char_freqs=dedup_prefix_full_char_freqs,
                max_code_length=max_code_length,
                charset=dedup_prefix_charset,
                min_score=dedup_prefix_min_score,
                short=False,
                full=dedup_prefix_full,
                short_levels=(),
                full_source_length=dedup_prefix_scheme_full_source_length or dedup_prefix_full_source_length,
                deep_rank_multiplier=dedup_prefix_deep_rank_multiplier,
            )
            prefix_counts.update(write_prefix_prototypes(
                scheme_entries_with_levels,
                {4: PREFIX_CODE_4_SICANG5_PATH},
            ))
        elif dedup_prefix_scheme == "wucang5":
            scheme_source_entries = shortcut_source_entries
            scheme_entries_with_levels = build_dedup_prefix_entries(
                scheme_source_entries,
                occupied_entries=scheme_source_entries,
                used_text_code=used_text_code,
                shortcut_leader_chars=shortcut_leader_chars,
                char_freqs=char_freqs,
                short_level_char_freqs=dedup_prefix_short_level_char_freqs,
                full_char_freqs=dedup_prefix_full_char_freqs,
                max_code_length=max_code_length,
                charset=dedup_prefix_charset,
                min_score=dedup_prefix_min_score,
                short=bool(dedup_prefix_scheme_short_levels),
                full=dedup_prefix_full,
                short_levels=dedup_prefix_scheme_short_levels,
                full_source_length=dedup_prefix_scheme_full_source_length or max_code_length,
                deep_rank_multiplier=dedup_prefix_deep_rank_multiplier,
            )
            prefix_counts.update(write_prefix_prototypes(
                scheme_entries_with_levels,
                {
                    4: PREFIX_CODE_4_WUCANG5_PATH,
                    5: PREFIX_CODE_5_WUCANG5_PATH,
                },
            ))
        elif dedup_prefix_full:
            scheme_source_entries = shortcut_source_entries
            scheme_entries_with_levels = build_dedup_prefix_entries(
                scheme_source_entries,
                occupied_entries=scheme_source_entries,
                used_text_code=used_text_code,
                shortcut_leader_chars=shortcut_leader_chars,
                char_freqs=char_freqs,
                short=False,
                full=True,
                max_code_length=max_code_length,
                charset=dedup_prefix_charset,
                min_score=dedup_prefix_min_score,
                full_source_length=dedup_prefix_full_source_length,
                deep_rank_multiplier=dedup_prefix_deep_rank_multiplier,
            )

        if scheme_entries_with_levels:
            append_prefix_entries(scheme_entries_with_levels)
    print(
        f"z/x 前缀消重：生成 {dedup_prefix_count} 个条目"
        f" 字集={dedup_prefix_charset} 最低分={dedup_prefix_min_score:g}"
        f" 短码={'开' if dedup_prefix_short else '关'}"
        f" 共享层级={','.join(str(level) for level in dedup_prefix_short_levels)}"
        f" 共享基线={dedup_prefix_source_max_code_length if dedup_prefix_source_max_code_length is not None else max_code_length}"
        f" 方案={dedup_prefix_scheme or 'legacy'}"
        f" 方案短码层级={','.join(str(level) for level in dedup_prefix_scheme_short_levels) or '-'}"
        f" 方案选重源长={dedup_prefix_scheme_full_source_length or dedup_prefix_full_source_length}"
    )
    if dedup_prefix:
        print(
            "z/x 前缀审阅文件："
            f" 2码={prefix_counts.get(2, 0)}"
            f" 3码={prefix_counts.get(3, 0)}"
            f" 4码={prefix_counts.get(4, 0)}"
            f" 5码={prefix_counts.get(5, 0)}"
        )

    if suffix_z:
        suffix_entries = build_z_suffix_entries(
            natural_shortcut_source_entries,
            occupied_entries=all_entries,
            used_text_code=used_text_code,
            shortcut_leader_chars=natural_shortcut_leader_chars,
            char_freqs=char_freqs,
            max_code_length=max_code_length,
            charset=suffix_z_charset,
            min_score=suffix_z_min_score,
            rank_suffixes=suffix_z_rank_suffixes,
            max_source_length=suffix_z_max_source_length,
            occupied_policy=suffix_z_occupied_policy,
        )
        z_suffix_count = len(suffix_entries)
        if suffix_code_path is not None:
            write_code_prototype(
                suffix_entries,
                suffix_code_path,
                title="自动 z/x 后缀审阅文件",
            )
        all_entries.extend(suffix_entries)
        all_entries.sort()
        shortcut_source_entries.extend(suffix_entries)
        shortcut_source_entries.sort()
        shortcut_leader_chars = build_shortcut_leader_chars(all_entries)
    print(
        f"z/x 后缀消重：生成 {z_suffix_count} 个条目"
        f" 字集={suffix_z_charset} 最低分={suffix_z_min_score:g}"
        f" 位次={','.join(f'{rank}:{suffix}' for rank, suffix in suffix_z_rank_suffixes)}"
        f" 源码最长={suffix_z_max_source_length if suffix_z_max_source_length is not None else max_code_length - 1}"
        f" 占用策略={suffix_z_occupied_policy}"
    )

    structure_suffix_count = 0
    if suffix_structure:
        structure_suffix_entries = build_structure_suffix_entries(
            shortcut_source_entries,
            occupied_entries=all_entries,
            used_text_code=used_text_code,
            shortcut_leader_chars=shortcut_leader_chars,
            char_freqs=char_freqs,
            max_code_length=max_code_length,
            suffix_structure_charset=suffix_structure_charset,
            suffix_structure_occupied_policy=suffix_structure_occupied_policy,
            suffix_structure_protect_min_score=suffix_structure_protect_min_score,
            suffix_structure_keymap=suffix_structure_keymap,
        )
        structure_suffix_count = len(structure_suffix_entries)
        all_entries.extend(structure_suffix_entries)
        all_entries.sort()
        print(f"结构后缀消重：生成 {structure_suffix_count} 个结构后缀条目")

    write_final_dict(
        output_path,
        all_entries,
        vocabulary=vocabulary,
        max_phrase_length=max_phrase_length,
        min_phrase_weight=min_phrase_weight,
    )

    sc_count = len(shortcut_entries)
    fc_count = len(fullcode_entries)
    print(
        f"完成：简码={sc_count} 全码={fc_count}"
        f" zx后缀={z_suffix_count} zx前缀={dedup_prefix_count} 结构后缀={structure_suffix_count}"
        f" 全码让位={'开' if fullcode_yield else '关'}"
        f" 全码让位门槛={fullcode_yield_min_score:g}"
        f" 总计={len(all_entries)} 输出={output_path}"
    )
