from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import DictEntry
from .paths import CHAR_FREQUENCY_SOURCES, WORD_FREQUENCY_SOURCES


WeightedSource = tuple[float, Path]


def load_frequency_table(path: Path) -> dict[str, float]:
    table: dict[str, float] = {}
    if not path.exists():
        return table

    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                table[parts[0]] = float(parts[1])
            except ValueError:
                continue
    return table


def load_weighted_scores(sources: list[WeightedSource]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for source_weight, path in sources:
        table = load_frequency_table(path)
        total = sum(table.values())
        if total <= 0:
            continue
        for text, frequency in table.items():
            scores[text] = scores.get(text, 0.0) + source_weight * frequency / total
    return scores


@dataclass(frozen=True)
class FrequencyScores:
    chars: dict[str, float]
    words: dict[str, float]

    def score_text(self, text: str) -> float:
        if len(text) == 1:
            return self.chars.get(text, 0.0)
        return self.words.get(text, 0.0)

    def score_entry(self, entry: DictEntry) -> float:
        if entry.source == "cangjie":
            return 0.0
        return self.score_text(entry.text)


def load_default_frequency_scores() -> FrequencyScores:
    return FrequencyScores(
        chars=load_weighted_scores(CHAR_FREQUENCY_SOURCES),
        words=load_weighted_scores(WORD_FREQUENCY_SOURCES),
    )
