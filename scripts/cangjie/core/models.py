from __future__ import annotations

from dataclasses import dataclass


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
