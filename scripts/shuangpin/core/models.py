from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharEntry:
    text: str
    pinyin: str
    sp: str
    aux: str
    code: str
    weight: int
    source: str = "chars"


@dataclass(frozen=True)
class WordEntry:
    text: str
    pinyin: str
    code: str
    weight: int
    length: int
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class DictEntry:
    text: str
    code: str
    weight: int
    tier: int
    source: str
    order: int = 0
