from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from .io import iter_rime_dict_rows
from .models import DictEntry
from .paths import CANGJIE5_DICT


LOW_PRIORITY_PREFIXES = ("x", "z")


def load_cangjie_codes(path: Path = CANGJIE5_DICT) -> dict[str, list[str]]:
    codes: dict[str, list[str]] = defaultdict(list)
    for parts in iter_rime_dict_rows(path):
        if len(parts) < 2:
            continue
        text, code = parts[0], parts[1]
        if len(text) == 1 and code:
            codes[text].append(code)
    return codes


def choose_cangjie_code(codes: list[str]) -> str:
    for code in codes:
        if not code.startswith(LOW_PRIORITY_PREFIXES):
            return code
    return codes[0]


def load_aux_map(path: Path = CANGJIE5_DICT) -> dict[str, str]:
    """Return first+last Cangjie auxiliary codes.

    Single-letter Cangjie codes are doubled so shuangpin character full codes
    are consistently four letters.
    """

    raw = load_cangjie_codes(path)
    aux: dict[str, str] = {}
    for text, codes in raw.items():
        code = choose_cangjie_code(codes)
        aux[text] = code + code if len(code) == 1 else code[0] + code[-1]
    return aux


def load_aux_lists(path: Path = CANGJIE5_DICT) -> dict[str, list[str]]:
    """Return all first+last auxiliary codes for external IME exports.

    This preserves the legacy Shouxin export behavior:
    non-x/z Cangjie codes come first, x/z compatibility codes are kept after
    them, and single-letter Cangjie codes stay single-letter.
    """

    raw = load_cangjie_codes(path)
    mapping: dict[str, list[str]] = {}
    for text, codes in raw.items():
        preferred: list[str] = []
        fallback: list[str] = []
        for code in codes:
            aux = code[0] + code[-1] if len(code) > 1 else code
            if code.startswith(LOW_PRIORITY_PREFIXES):
                if aux not in preferred and aux not in fallback:
                    fallback.append(aux)
            elif aux not in preferred:
                preferred.append(aux)
        auxes = preferred + fallback
        if auxes:
            mapping[text] = auxes
    return mapping


def build_prefixed_cangjie_entries(
    path: Path = CANGJIE5_DICT,
    prefix: str = "o",
    weight: int = -1000000,
    tier: int = 90,
) -> list[DictEntry]:
    entries: list[DictEntry] = []
    seen: set[tuple[str, str]] = set()
    for text, codes in load_cangjie_codes(path).items():
        if not codes:
            continue
        code = choose_cangjie_code(codes)
        out_code = prefix + code
        key = (text, out_code)
        if key in seen:
            continue
        seen.add(key)
        entries.append(DictEntry(text=text, code=out_code, weight=weight, tier=tier, source="cangjie"))
    return entries
