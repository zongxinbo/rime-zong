from __future__ import annotations

from pathlib import Path

from .cangjie import load_aux_lists
from .paths import CHARS_SOURCE, PROTOTYPES_DIR


SHOUXIN_AUX_PATH = PROTOTYPES_DIR / "cangjie_aux.txt"


def load_source_chars(chars_path: Path = CHARS_SOURCE) -> set[str]:
    chars: set[str] = set()
    with chars_path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if parts:
                chars.add(parts[0])
    return chars


def export_shouxin_aux(output_path: Path = SHOUXIN_AUX_PATH) -> int:
    """Export GBK-compatible auxiliary codes for Shouxin input method."""

    source_chars = load_source_chars()
    aux_lists = load_aux_lists()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for text, auxes in aux_lists.items():
            if text not in source_chars:
                continue
            try:
                text.encode("gbk")
            except UnicodeEncodeError:
                continue
            for aux in auxes:
                f.write(f"{text}={aux}\n")
                count += 1
    return count

