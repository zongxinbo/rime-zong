from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from .charset import is_han_char, is_han_text
from .models import FrequencyEntry
from .paths import FREQ_PATHS, FREQ_WEIGHTS


def parse_frequency_file(path: Path) -> tuple[dict[str, int], list[FrequencyEntry]]:
    """读取频率文件，提取单字频率和词语频率。"""
    char_frequencies: dict[str, int] = {}
    phrase_frequencies: dict[str, int] = {}

    if not path.is_file():
        return char_frequencies, []

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line or line.startswith("#"):
            continue

        parts = line.split("\t")
        if len(parts) < 2:
            continue

        text, weight_text = parts[0], parts[1]

        try:
            weight = int(weight_text)
        except ValueError as exc:
            raise ValueError(f"{path}:{lineno}: 遇到异常词频 {weight_text!r}") from exc

        if is_han_char(text):
            if weight > char_frequencies.get(text, -1):
                char_frequencies[text] = weight
        elif len(text) > 1 and is_han_text(text):
            if weight > phrase_frequencies.get(text, -1):
                phrase_frequencies[text] = weight

    phrases = [
        FrequencyEntry(text=text, weight=weight)
        for text, weight in phrase_frequencies.items()
    ]
    return char_frequencies, phrases


def get_weighted_frequencies() -> dict[str, int]:
    """计算多份语料库的加权得分并返回合并后的字典。"""
    char_scores = defaultdict(int)
    for name, path in FREQ_PATHS.items():
        if path.exists():
            weight = FREQ_WEIGHTS.get(name, 1)
            freqs, _ = parse_frequency_file(path)
            for char, val in freqs.items():
                char_scores[char] += val * weight
        else:
            print(f"Warning: Frequency file not found: {path}", file=sys.stderr)
    return char_scores
