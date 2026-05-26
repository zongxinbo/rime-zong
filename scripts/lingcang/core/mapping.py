from __future__ import annotations

from dataclasses import dataclass


B_KEYS = frozenset("aeiou")
A_KEYS = frozenset("bcdfghjklmnpqrstvwxyz")


# Original Cangjie root key -> A-zone key.
DEFAULT_A_ZONE_MAP: dict[str, str] = {
    "a": "n",  # 日 / 弓
    "b": "b",  # 月
    "c": "c",  # 金 / 人
    "d": "d",  # 木
    "e": "z",  # 水
    "f": "f",  # 火
    "g": "g",  # 土
    "h": "h",  # 竹
    "i": "x",  # 戈 / 難
    "j": "j",  # 十
    "k": "k",  # 大
    "l": "l",  # 中
    "m": "m",  # 一
    "n": "n",  # 弓 / 日
    "o": "c",  # 人 / 金
    "p": "p",  # 心
    "q": "q",  # 手
    "r": "r",  # 口
    "s": "s",  # 尸
    "t": "t",  # 廿
    "u": "w",  # 山 / 田
    "v": "v",  # 女 / 人
    "w": "w",  # 田 / 山
    "x": "x",  # 難 / 戈
    "y": "y",  # 卜 / 戈
}


# Original Cangjie root key -> B-zone final key, based on root-name vowel onset.
DEFAULT_B_ZONE_MAP: dict[str, str] = {
    "a": "i",  # 日 ri
    "b": "u",  # 月 yue
    "c": "i",  # 金 jin
    "d": "u",  # 木 mu
    "e": "u",  # 水 shui
    "f": "u",  # 火 huo
    "g": "u",  # 土 tu
    "h": "u",  # 竹 zhu
    "i": "e",  # 戈 ge
    "j": "i",  # 十 shi
    "k": "a",  # 大 da
    "l": "o",  # 中 zhong
    "m": "i",  # 一 yi
    "n": "o",  # 弓 gong
    "o": "e",  # 人 ren
    "p": "i",  # 心 xin
    "q": "o",  # 手 shou
    "r": "o",  # 口 kou
    "s": "i",  # 尸 shi
    "t": "i",  # 廿 nian
    "u": "a",  # 山 shan
    "v": "u",  # 女 nv
    "w": "i",  # 田 tian
    "x": "a",  # 難 nan
    "y": "u",  # 卜 bu
}


@dataclass(frozen=True)
class EncodedChar:
    text: str
    source_code: str
    code: str
    weight: int


def project_cangjie4(code: str) -> str:
    if len(code) <= 4:
        return code
    return code[:3] + code[-1]


def encode_lingcang(source_code: str) -> str:
    return encode_with_maps(source_code, DEFAULT_A_ZONE_MAP, DEFAULT_B_ZONE_MAP)


def encode_with_maps(source_code: str, a_zone_map: dict[str, str], b_zone_map: dict[str, str]) -> str:
    projected = project_cangjie4(source_code)
    if any(ch not in a_zone_map for ch in projected):
        raise KeyError(source_code)
    if len(projected) < 4:
        body = "".join(a_zone_map[ch] for ch in projected)
        return body + b_zone_map[projected[-1]]
    return "".join(a_zone_map[ch] for ch in projected)
