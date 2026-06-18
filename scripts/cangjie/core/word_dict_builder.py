from __future__ import annotations

import bisect
import datetime as _dt
from dataclasses import dataclass
from pathlib import Path

from opencc import OpenCC

from .frequency import get_weighted_frequencies, parse_frequency_file
from .io import parse_cangjie_dict
from .paths import ONE_CODE_PATH, ROOT_CODE_PATH, SC_GLYPH_PREFERRED_CODE_PATH
from .weight_profiles import get_weight_profile


@dataclass(frozen=True)
class DictRow:
    text: str
    code: str
    order: int
    is_phrase: bool
    score: int
    phrase_order: int = 0
    phrase_variant_order: int = 0
    demote_full_code_for_phrase: bool = False


def read_words_dict(path: Path) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()
    in_body = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "...":
            in_body = True
            continue
        if not in_body or not line or line.startswith("#"):
            continue
        word = line.split("\t", 1)[0].strip()
        if word and word not in seen:
            seen.add(word)
            words.append(word)
    return words


def read_prototype_codes(path: Path) -> dict[str, str]:
    codes: dict[str, str] = {}
    if not path.exists():
        return codes
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "\t" not in line:
            continue
        text, code = line.split("\t", 1)
        text = text.strip()
        code = code.strip()
        if text and code:
            codes[text] = code
    return codes


def build_quantile_mapper(sc_scores: dict[str, int], essay_scores: dict[str, int]):
    shared_chars = [
        char
        for char, score in sc_scores.items()
        if score > 0 and essay_scores.get(char, 0) > 0
    ]
    if not shared_chars:
        return lambda score: 0

    sc_sorted = sorted(sc_scores[char] for char in shared_chars)
    essay_sorted = sorted(essay_scores[char] for char in shared_chars)

    def map_score(score: int) -> int:
        if score <= 0:
            return 0
        index = bisect.bisect_left(sc_sorted, score)
        if index >= len(essay_sorted):
            index = len(essay_sorted) - 1
        return essay_sorted[index]

    return map_score


def single_score(
    text: str,
    *,
    essay_char_scores: dict[str, int],
    sc_daily_scores: dict[str, int],
    map_sc_to_essay,
) -> int:
    score = essay_char_scores.get(text, 0)
    if score > 0:
        return score
    return map_sc_to_essay(sc_daily_scores.get(text, 0))


def phrase_score(
    text: str,
    *,
    converter: OpenCC,
    essay_phrase_scores: dict[str, int],
    essay_phrase_order: dict[str, int],
) -> tuple[int, int, int]:
    simplified = converter.convert(text)
    score = essay_phrase_scores.get(simplified, 0)
    order = essay_phrase_order.get(simplified, 0)
    variant_order = 0 if text == simplified else 1
    return score, order, variant_order


def phrase_code(word: str, base_codes: dict[str, str]) -> str | None:
    codes = []
    for char in word:
        code = base_codes.get(char)
        if not code:
            return None
        codes.append(code)

    if len(codes) == 2:
        return codes[0][:2] + codes[1][:2]
    if len(codes) == 3:
        return codes[0][:1] + codes[1][:1] + codes[2][:2]
    if len(codes) >= 4:
        return codes[0][:1] + codes[1][:1] + codes[2][:1] + codes[-1][:1]
    return None


def usable_word_base_code(text: str, code: str, one_codes: dict[str, str]) -> bool:
    return (
        len(text) == 1
        and bool(code)
        and not code.startswith(("z", "x"))
        and code != one_codes.get(text)
    )


def choose_base_codes(
    entries,
    *,
    root_codes: dict[str, str],
    one_codes: dict[str, str],
    preferred_codes: dict[str, str],
) -> tuple[dict[str, str], int]:
    char_codes: dict[str, list[str]] = {}
    seen_char_codes: set[tuple[str, str]] = set()
    for entry in entries:
        if entry.text in root_codes:
            continue
        if not usable_word_base_code(entry.text, entry.code, one_codes):
            continue
        key = (entry.text, entry.code)
        if key in seen_char_codes:
            continue
        seen_char_codes.add(key)
        char_codes.setdefault(entry.text, []).append(entry.code)

    base_codes: dict[str, str] = dict(root_codes)
    preferred_used = 0
    for char, codes in char_codes.items():
        preferred = preferred_codes.get(char)
        if preferred and len(codes) > 1 and preferred in codes:
            base_codes[char] = preferred
            preferred_used += 1
        else:
            base_codes[char] = codes[0]
    return base_codes, preferred_used


def merge_code_group(rows: list[DictRow]) -> list[DictRow]:
    singles = [row for row in rows if not row.is_phrase]
    phrases = sorted(
        (row for row in rows if row.is_phrase),
        key=lambda row: (-row.score, row.phrase_variant_order, row.phrase_order, row.text),
    )
    if not singles:
        return phrases

    merged: list[DictRow] = []
    phrase_index = 0
    for single in singles:
        while (
            phrase_index < len(phrases)
            and (single.demote_full_code_for_phrase or phrases[phrase_index].score > single.score)
        ):
            merged.append(phrases[phrase_index])
            phrase_index += 1
        merged.append(single)
    merged.extend(phrases[phrase_index:])
    return merged


def collect_shorter_code_flags(entries) -> dict[tuple[str, str], bool]:
    codes_by_char: dict[str, set[str]] = {}
    for entry in entries:
        if len(entry.text) == 1 and entry.code and not entry.code.startswith(("z", "x")):
            codes_by_char.setdefault(entry.text, set()).add(entry.code)

    flags: dict[tuple[str, str], bool] = {}
    for text, codes in codes_by_char.items():
        for code in codes:
            flags[(text, code)] = any(len(other) < len(code) for other in codes)
    return flags

def build_word_dict(
    *,
    source_dict: Path,
    words_dict: Path,
    essay_path: Path,
    output_path: Path,
    name: str,
    root_code_path: Path = ROOT_CODE_PATH,
    one_code_path: Path = ONE_CODE_PATH,
    preferred_code_path: Path = SC_GLYPH_PREFERRED_CODE_PATH,
) -> dict[str, int]:
    entries = parse_cangjie_dict(source_dict)
    root_codes = read_prototype_codes(root_code_path)
    one_codes = read_prototype_codes(one_code_path)
    preferred_codes = read_prototype_codes(preferred_code_path)
    shorter_code_flags = collect_shorter_code_flags(entries)
    base_codes, preferred_used = choose_base_codes(
        entries,
        root_codes=root_codes,
        one_codes=one_codes,
        preferred_codes=preferred_codes,
    )
    converter = OpenCC("t2s")
    essay_char_scores, essay_phrases = parse_frequency_file(essay_path)
    essay_phrase_scores = {entry.text: entry.weight for entry in essay_phrases}
    essay_phrase_order = {entry.text: index for index, entry in enumerate(essay_phrases)}
    sc_daily_scores = get_weighted_frequencies(get_weight_profile("sc_daily"))
    map_sc_to_essay = build_quantile_mapper(sc_daily_scores, essay_char_scores)

    rows_by_code: dict[str, list[DictRow]] = {}
    seen_text_code: set[tuple[str, str]] = set()
    for order, entry in enumerate(entries):
        if not entry.text or not entry.code:
            continue
        if len(entry.text) == 1:
            score = single_score(
                entry.text,
                essay_char_scores=essay_char_scores,
                sc_daily_scores=sc_daily_scores,
                map_sc_to_essay=map_sc_to_essay,
            )
            phrase_order = 0
            phrase_variant_order = 0
            demote_full_code_for_phrase = shorter_code_flags.get((entry.text, entry.code), False)
        else:
            score, phrase_order, phrase_variant_order = phrase_score(
                entry.text,
                converter=converter,
                essay_phrase_scores=essay_phrase_scores,
                essay_phrase_order=essay_phrase_order,
            )
            demote_full_code_for_phrase = False

        row = DictRow(
            text=entry.text,
            code=entry.code,
            order=order,
            is_phrase=len(entry.text) > 1,
            score=score,
            phrase_order=phrase_order,
            phrase_variant_order=phrase_variant_order,
            demote_full_code_for_phrase=demote_full_code_for_phrase,
        )
        key = (row.text, row.code)
        if key in seen_text_code:
            continue
        seen_text_code.add(key)
        rows_by_code.setdefault(row.code, []).append(row)

    words = read_words_dict(words_dict)
    phrase_seen = 0
    phrase_kept = 0
    phrase_dropped_not_in_essay = 0
    phrase_dropped_missing_code = 0
    phrase_dropped_duplicate = 0
    for word in words:
        if len(word) < 2:
            continue
        phrase_seen += 1
        score, phrase_order, phrase_variant_order = phrase_score(
            word,
            converter=converter,
            essay_phrase_scores=essay_phrase_scores,
            essay_phrase_order=essay_phrase_order,
        )
        if score <= 0:
            phrase_dropped_not_in_essay += 1
            continue
        code = phrase_code(word, base_codes)
        if code is None:
            phrase_dropped_missing_code += 1
            continue
        key = (word, code)
        if key in seen_text_code:
            phrase_dropped_duplicate += 1
            continue
        seen_text_code.add(key)
        phrase_kept += 1
        rows_by_code.setdefault(code, []).append(DictRow(
            text=word,
            code=code,
            order=len(entries) + phrase_seen,
            is_phrase=True,
            score=score,
            phrase_order=phrase_order,
            phrase_variant_order=phrase_variant_order,
        ))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        file.write("# encoding: utf-8\n")
        file.write("# 由 scripts/cangjie/gen_*_words.py 生成\n")
        file.write("---\n")
        file.write(f"name: {name}\n")
        file.write(f"version: '{_dt.date.today().isoformat()}'\n")
        file.write("sort: by_original\n")
        file.write("...\n\n")
        for code in sorted(rows_by_code):
            rows = sorted(rows_by_code[code], key=lambda row: row.order)
            for row in merge_code_group(rows):
                file.write(f"{row.text}\t{row.code}\n")

    return {
        "single_rows": sum(1 for row in seen_text_code if len(row[0]) == 1),
        "phrase_seen": phrase_seen,
        "phrase_kept": phrase_kept,
        "phrase_dropped_not_in_essay": phrase_dropped_not_in_essay,
        "phrase_dropped_missing_code": phrase_dropped_missing_code,
        "phrase_dropped_duplicate": phrase_dropped_duplicate,
        "root_base_codes": len(root_codes),
        "one_shortcut_codes": len(one_codes),
        "preferred_base_codes": preferred_used,
    }
