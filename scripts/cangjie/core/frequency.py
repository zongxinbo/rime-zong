from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from .charset import is_han_char, is_han_text
from .models import FrequencyEntry
from .paths import (
    FREQ_PATHS,
    SC_FREQ_WEIGHTS,
    SC_BALANCED_FREQ_WEIGHTS
)


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
    """计算多份语料库的加权得分并返回合并后的字典（采用相对频率归一化算法）。"""
    if weights is None:
        weights = SC_FREQ_WEIGHTS

    # 1. 提取权重为正的活跃语料
    active_sources = {name: w for name, w in weights.items() if w > 0}

    # 2. 读入各语料并进行相对频率归一化
    normalized_freqs = {}
    allowed_chars = set()

    for name in active_sources:
        path = FREQ_PATHS.get(name)
        if path and path.exists():
            freqs, _ = parse_frequency_file(path)
            total = sum(freqs.values())
            if total > 0:
                normalized_freqs[name] = {k: v / total for k, v in freqs.items()}
                allowed_chars.update(freqs.keys())
        else:
            print(f"Warning: Frequency file not found for {name}", file=sys.stderr)

    # 3. 合并加权并放大至 10^9 比例
    char_scores = {}
    for char in allowed_chars:
        score = 0.0
        for name, w in active_sources.items():
            if name in normalized_freqs:
                score += w * normalized_freqs[name].get(char, 0.0)
        char_scores[char] = int(score * 10**9)

    return char_scores