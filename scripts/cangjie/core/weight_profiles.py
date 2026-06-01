"""仓颉简码评估共用的字频权重模式。"""

from __future__ import annotations

from .paths import SC_BALANCED_FREQ_WEIGHTS, SC_FREQ_WEIGHTS


WEIGHT_PROFILES = {
    "sc": SC_FREQ_WEIGHTS,
    "sc_balanced": SC_BALANCED_FREQ_WEIGHTS,
}

WEIGHT_PROFILE_DESCRIPTIONS = {
    "sc": "日常简体优先：口语 6、字幕 5、知乎 4、北语 2、Essay 1",
    "sc_balanced": "简繁平衡：知乎 33%、北语 27%、台标 22%、古籍 18%",
}


def get_weight_profile(name: str) -> dict[str, float]:
    try:
        return WEIGHT_PROFILES[name]
    except KeyError as exc:
        choices = "、".join(WEIGHT_PROFILES)
        raise ValueError(f"权重模式只能是 {choices}") from exc


def describe_weight_profile(name: str) -> str:
    get_weight_profile(name)
    return WEIGHT_PROFILE_DESCRIPTIONS[name]
