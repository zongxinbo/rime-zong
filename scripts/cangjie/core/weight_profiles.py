"""仓颉简码评估共用的字频权重模式。"""

from __future__ import annotations

from .paths import SC_BALANCED_FREQ_WEIGHTS, SC_DAILY_FREQ_WEIGHTS, SC_FREQ_WEIGHTS, TC_FREQ_WEIGHTS


WEIGHT_PROFILES = {
    "sc": SC_FREQ_WEIGHTS,
    "sc_daily": SC_DAILY_FREQ_WEIGHTS,
    "sc_balanced": SC_BALANCED_FREQ_WEIGHTS,
    "tc": TC_FREQ_WEIGHTS,
}

WEIGHT_PROFILE_DESCRIPTIONS = {
    "sc": "现代简体日用优化：口语 20.75%、字幕 27.57%、知乎 27.92%、北语 23.76%",
    "sc_daily": "简繁日常通用：知乎 44%、北语 36%、台标 11%、古籍 9%",
    "sc_balanced": "简繁平衡：知乎 33%、北语 27%、台标 22%、古籍 18%",
    "tc": "现代繁体日用优化：台标 100%",
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
