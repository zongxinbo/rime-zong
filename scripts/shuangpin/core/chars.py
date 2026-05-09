from __future__ import annotations

from pathlib import Path
from typing import Callable

from .cangjie import load_aux_map
from .io import parse_int
from .models import CharEntry
from .paths import CANGJIE5_DICT, CHARS_HEADER_TEMPLATE, CHARS_SOURCE


Converter = Callable[[str], str]


def load_radical_entries(
    converter: Converter,
    aux_map: dict[str, str],
    template_path: Path = CHARS_HEADER_TEMPLATE,
) -> tuple[list[CharEntry], set[str]]:
    entries: list[CharEntry] = []
    dropped: set[str] = set()
    in_body = False

    with template_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if line.strip() == "...":
                in_body = True
                continue
            if not in_body:
                continue
            if not line.strip() or line.startswith("#") or "\t" not in line:
                continue
            parts = line.split("\t")
            if len(parts) < 2 or ";" not in parts[1]:
                continue
            text = parts[0]
            sp = parts[1].split(";", 1)[0]
            weight = parse_int(parts[2], 0) if len(parts) >= 3 else 0
            aux = aux_map.get(text)
            if not aux:
                dropped.add(text)
                continue
            entries.append(
                CharEntry(
                    text=text,
                    pinyin="",
                    sp=sp,
                    aux=aux,
                    code=sp + aux,
                    weight=weight,
                    source="radicals",
                )
            )
    return entries, dropped


def load_char_source(
    converter: Converter,
    aux_map: dict[str, str],
    chars_path: Path = CHARS_SOURCE,
    simplified: bool = False,
) -> tuple[list[CharEntry], set[str]]:
    entries: list[CharEntry] = []
    dropped: set[str] = set()
    weight_index = 3 if simplified else 2

    with chars_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) <= weight_index:
                continue
            text, pinyin = parts[0], parts[1]
            aux = aux_map.get(text)
            if not aux:
                dropped.add(text)
                continue
            try:
                sp = converter(pinyin)
            except Exception:
                dropped.add(text)
                continue
            entries.append(
                CharEntry(
                    text=text,
                    pinyin=pinyin,
                    sp=sp,
                    aux=aux,
                    code=sp + aux,
                    weight=parse_int(parts[weight_index], 0),
                )
            )
    return entries, dropped


def build_char_entries(
    converter: Converter,
    simplified: bool = False,
    cangjie_path: Path = CANGJIE5_DICT,
) -> tuple[list[CharEntry], set[str]]:
    aux_map = load_aux_map(cangjie_path)
    radicals, dropped_radicals = load_radical_entries(converter, aux_map)
    chars, dropped_chars = load_char_source(converter, aux_map, simplified=simplified)
    return radicals + chars, dropped_radicals | dropped_chars


def write_chars_prototype(entries: list[CharEntry], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("# text\tpinyin\tsp\taux\tcode\tweight\tsource\n")
        for entry in entries:
            f.write(
                f"{entry.text}\t{entry.pinyin}\t{entry.sp}\t{entry.aux}\t"
                f"{entry.code}\t{entry.weight}\t{entry.source}\n"
            )

