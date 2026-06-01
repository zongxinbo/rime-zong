from __future__ import annotations

import sys
from math import fsum
from pathlib import Path

from .charset import is_han_char, is_han_text
from .models import FrequencyEntry
from .paths import (
    FREQ_PATHS,
    SC_FREQ_WEIGHTS,
)

FREQUENCY_SCORE_SCALE = 10**9


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


def get_weighted_frequencies(weights: dict[str, float] | None = None) -> dict[str, int]:
    """按语料相对频率和来源权重计算固定分制的综合字频。"""
    if weights is None:
        weights = SC_FREQ_WEIGHTS

    # 仅使用成功读取的非空语料，避免缺失来源改变综合分的量级。
    active_sources = {name: w for name, w in weights.items() if w > 0}
    normalized_freqs: dict[str, dict[str, float]] = {}
    allowed_chars: set[str] = set()
    for name in active_sources:
        path = FREQ_PATHS.get(name)
        if path and path.exists():
            freqs, _ = parse_frequency_file(path)
            total = sum(freqs.values())
            if total > 0:
                normalized_freqs[name] = {k: v / total for k, v in freqs.items()}
                allowed_chars.update(freqs.keys())
            else:
                print(f"Warning: Frequency file is empty for {name}: {path}", file=sys.stderr)
        else:
            print(f"Warning: Frequency file not found for {name}", file=sys.stderr)

    usable_weights = {
        name: weight
        for name, weight in active_sources.items()
        if name in normalized_freqs
    }
    total_weight = fsum(usable_weights.values())
    if total_weight <= 0:
        return {}

    char_scores = {}
    for char in allowed_chars:
        score = fsum(
            weight * normalized_freqs[name].get(char, 0.0)
            for name, weight in usable_weights.items()
        )
        char_scores[char] = round(score / total_weight * FREQUENCY_SCORE_SCALE)

    return char_scores
