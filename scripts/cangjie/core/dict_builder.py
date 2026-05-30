from __future__ import annotations

import datetime as _dt
from collections import defaultdict
from pathlib import Path

from .charset import is_common_han_char, is_han_char, suffix_structure_charset_allows
from .code_utils import build_fullcode_yield_order, build_shortcut_leader_chars, project_code
from .dedup import build_dedup_prefix_entries, build_z_suffix_entries, unique_seen_entries
from .frequency import parse_frequency_file
from .ids import load_ids_structure_map
from .io import parse_cangjie_dict
from .paths import DEFAULT_FULLCODE_YIELD_MIN_SCORE


def load_shortcut_entries(shortcut_paths: dict) -> tuple[list[tuple[str, str, int | float]], set[str]]:
    """加载 Z/S1/S2/S3/S4 简码原型。"""
    shortcut_entries: list[tuple[str, str, int | float]] = []
    z_root_chars: set[str] = set()

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
                        z_root_chars.add(char)

    load_shortcut(shortcut_paths.get("z"), 0)
    load_shortcut(shortcut_paths.get(1), 1)
    load_shortcut(shortcut_paths.get("fixed_prefix"), 1.5)
    load_shortcut(shortcut_paths.get(2), 2)
    load_shortcut(shortcut_paths.get(3), 3)
    load_shortcut(shortcut_paths.get(4), 4)
    return shortcut_entries, z_root_chars


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
    z_root_chars: set[str],
    used_text_code: set[tuple[str, str]],
    char_freqs: dict[str, int],
    max_code_length: int,
) -> list[tuple[str, str, int]]:
    fullcode_entries: list[tuple[str, str, int]] = []
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
    return fullcode_entries


def build_base_entries(
    shortcut_entries: list[tuple[str, str, int | float]],
    fullcode_entries: list[tuple[str, str, int]],
    *,
    char_freqs: dict[str, int],
    fullcode_yield_min_score: float,
) -> list[tuple[str, int | float, int, int, str]]:
    all_entries: list[tuple[str, int, int, int, str]] = []
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
    return all_entries


def build_structure_suffix_entries(
    all_entries: list[tuple[str, int, int, int, str]],
    *,
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
    dedup_prefix: bool = True,
    dedup_prefix_charset: str = "frequency",
    dedup_prefix_min_score: float = 1,
    suffix_structure: bool = False,
    suffix_structure_charset: str = "gbk",
    suffix_structure_occupied_policy: str = "protect-min-score",
    suffix_structure_protect_min_score: float = 100000,
    suffix_structure_keymap: str = "zxwa",
):
    """生成最终字典。"""
    print(f"正在解析原始仓颉编码: {source_dict}...")
    char_full_codes = collect_char_full_codes(
        source_dict,
        exclude_extended=exclude_extended,
        only_first_full_code=only_first_full_code,
    )

    print("正在加载简码规则...")
    shortcut_entries, z_root_chars = load_shortcut_entries(shortcut_paths)

    print("正在生成单字...")
    if char_freqs is None:
        char_freqs, _ = parse_frequency_file(freq_file)
    else:
        print("使用预加载的加权字频数据进行排序...")

    used_text_code = {(char, code) for char, code, _ in shortcut_entries}
    fullcode_entries = build_fullcode_entries(
        char_full_codes,
        z_root_chars=z_root_chars,
        used_text_code=used_text_code,
        char_freqs=char_freqs,
        max_code_length=max_code_length,
    )
    all_entries = build_base_entries(
        shortcut_entries,
        fullcode_entries,
        char_freqs=char_freqs,
        fullcode_yield_min_score=fullcode_yield_min_score,
    )
    shortcut_leader_chars = build_shortcut_leader_chars(all_entries)

    z_suffix_count = 0
    if suffix_z:
        suffix_entries = build_z_suffix_entries(
            all_entries,
            used_text_code=used_text_code,
            shortcut_leader_chars=shortcut_leader_chars,
            char_freqs=char_freqs,
            max_code_length=max_code_length,
        )
        z_suffix_count = len(suffix_entries)
        all_entries.extend(suffix_entries)
        all_entries.sort()
    print(f"z 后缀消重：生成 {z_suffix_count} 个条目")

    dedup_prefix_count = 0
    if dedup_prefix:
        dedup_prefix_entries = build_dedup_prefix_entries(
            all_entries,
            used_text_code=used_text_code,
            shortcut_leader_chars=shortcut_leader_chars,
            char_freqs=char_freqs,
            max_code_length=max_code_length,
            charset=dedup_prefix_charset,
            min_score=dedup_prefix_min_score,
        )
        dedup_prefix_count = len(dedup_prefix_entries)
        all_entries.extend(dedup_prefix_entries)
        all_entries.sort()
    print(
        f"z/x 前缀消重：生成 {dedup_prefix_count} 个条目"
        f" 字集={dedup_prefix_charset} 最低分={dedup_prefix_min_score:g}"
    )

    structure_suffix_count = 0
    if suffix_structure:
        structure_suffix_entries = build_structure_suffix_entries(
            all_entries,
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
        f" z后缀={z_suffix_count} zx前缀={dedup_prefix_count} 结构后缀={structure_suffix_count}"
        f" 全码让位门槛={fullcode_yield_min_score:g}"
        f" 总计={len(all_entries)} 输出={output_path}"
    )
