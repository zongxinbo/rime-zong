from __future__ import annotations

from pathlib import Path
from typing import Callable

from .cangjie import load_aux_map
from .io import iter_rime_dict_rows, parse_int
from .models import WordEntry
from .paths import CANGJIE5_DICT, PINYIN_SIMP_DICT


Converter = Callable[[str], str]


def is_han_word(text: str) -> bool:
    return len(text) >= 2 and all("\u3400" <= ch <= "\u9fff" for ch in text)


def encode_word(text: str, pinyin: str, converter: Converter, aux_map: dict[str, str]) -> str | None:
    syllables = pinyin.split()
    if len(syllables) != len(text):
        return None

    try:
        sps = [converter(syllable) for syllable in syllables]
    except Exception:
        return None

    if any(len(sp) != 2 for sp in sps):
        return None

    auxes = [aux_map.get(ch) for ch in text]
    if any(not aux for aux in auxes):
        return None

    first_aux = auxes[0][0]
    last_aux = auxes[-1][0]

    if len(text) == 2:
        return sps[0] + sps[1] + first_aux + last_aux
    if len(text) == 3:
        return sps[0][0] + sps[1][0] + sps[2] + first_aux + last_aux
    if len(text) == 4:
        return sps[0][0] + sps[1][0] + sps[2][0] + sps[3][0] + first_aux + last_aux
    return sps[0][0] + sps[1][0] + sps[2][0] + sps[-1][0] + first_aux + last_aux


def build_word_entries(
    converter: Converter,
    source_path: Path = PINYIN_SIMP_DICT,
    cangjie_path: Path = CANGJIE5_DICT,
    min_weight: int = 1,
    max_length: int = 8,
) -> tuple[list[WordEntry], int]:
    aux_map = load_aux_map(cangjie_path)
    entries: list[WordEntry] = []
    dropped = 0
    seen: dict[tuple[str, str], WordEntry] = {}

    for parts in iter_rime_dict_rows(source_path):
        if len(parts) < 2:
            continue
        text, pinyin = parts[0], parts[1]
        weight = parse_int(parts[2], 0) if len(parts) >= 3 else 0
        if weight < min_weight or len(text) > max_length or not is_han_word(text):
            continue
        code = encode_word(text, pinyin, converter, aux_map)
        if not code:
            dropped += 1
            continue
        entry = WordEntry(text=text, pinyin=pinyin, code=code, weight=weight, length=len(text))
        key = (text, code)
        old = seen.get(key)
        if old is None or entry.weight > old.weight:
            seen[key] = entry

    entries.extend(seen.values())
    entries.sort(key=lambda e: (e.code, -e.weight, e.text))
    return entries, dropped


def write_words_prototype(entries: list[WordEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# text\tpinyin\tcode\tweight\tlength\n")
        for entry in entries:
            f.write(f"{entry.text}\t{entry.pinyin}\t{entry.code}\t{entry.weight}\t{entry.length}\n")

