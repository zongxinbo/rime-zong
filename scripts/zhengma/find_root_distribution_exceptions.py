#!/usr/bin/env python3
"""生成郑码字根分布中需要死记的归并/分流清单。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOTS = SCRIPT_DIR / "data" / "roots.txt"
DEFAULT_OUTPUT = SCRIPT_DIR / "data" / "root_distribution_exceptions.md"


@dataclass(frozen=True)
class RootGroup:
    name: str
    roots: tuple[str, ...]
    reason: str


ROOT_GROUPS = [
    RootGroup("言类", ("言", "讠", "訁"), "讠按表层像点折，但归并到言类 S 区。"),
    RootGroup("金类", ("金", "钅", "釒"), "钅/釒按金类统一在 P 区。"),
    RootGroup("食类", ("食", "飠", "饣", "⻞"), "食字和食旁统一在 OX。"),
    RootGroup("糸类", ("纟", "糸", "糹"), "简繁绞丝统一在 Z 区。"),
    RootGroup("长类", ("长", "長"), "简繁形差异较大，但统一在 CH。"),
    RootGroup("丰类", ("丰", "豐"), "简繁/部件形统一在 CI。"),
    RootGroup("贝类", ("贝", "貝"), "简繁贝统一在 LO。"),
    RootGroup("见类", ("见", "見"), "简繁见统一在 LR。"),
    RootGroup("页类", ("页", "頁"), "简繁页统一在 GO。"),
    RootGroup("鸟类", ("鸟", "{鸟上}", "鳥", "{鳥上}", "{鳥}"), "鸟类统一在 RZ。"),
    RootGroup("乌类", ("乌", "烏", "{烏上}", "{烏}"), "乌类统一在 RZA，不能只按鸟类 RZ 推。"),
    RootGroup("鱼类", ("鱼", "{鱼上}", "魚"), "鱼类统一在 R 区。"),
    RootGroup("气类", ("气", "氣"), "简繁气统一在 MY。"),
    RootGroup("齿类", ("齿", "齒"), "简繁齿统一在 IO。"),
    RootGroup("龙类", ("龙", "龍"), "简繁龙不在同区：龙 GM，龍 SI。"),
    RootGroup("马类", ("马", "馬", "{馬上}", "{馬}"), "简繁马不在同区：马 X，馬 CU。"),
    RootGroup("车类", ("车", "車", "{車}"), "简繁车不在同区：车 HE，車 FK。"),
    RootGroup("门类", ("门", "門", "{門}"), "简繁门不在同区：门 TL，門 XD。"),
    RootGroup("示衣旁", ("示", "礻", "衤"), "示、示旁、衣旁分布不同：示 BK，礻 WS，衤 WT。"),
    RootGroup("心水旁", ("忄", "心", "氵", "水"), "心旁/心字、水旁/水字分布不同，不能只按点形推。"),
    RootGroup("刀类", ("刂", "刀"), "立刀旁和刀字分区不同：刂 KD，刀 YD。"),
    RootGroup("简繁部件分流", ("无", "{無中}", "{帶上}", "{带上}", "{尧上}"), "部分简繁或残件不按同一成字根分布，需要按表记。"),
]


def read_roots(path: Path) -> dict[str, tuple[str, str]]:
    roots: dict[str, tuple[str, str]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        roots[parts[0]] = (parts[1], parts[2] if len(parts) >= 3 else "")
    return roots


def root_char_code(component_code: str, suffix: str) -> str:
    if suffix == "*":
        return f"{component_code}*"
    return component_code + suffix


def render_markdown(roots: dict[str, tuple[str, str]]) -> str:
    lines = [
        "# 郑码字根分布例外清单",
        "",
        "本文由 `scripts/zhengma/find_root_distribution_exceptions.py` 生成。",
        "用于记录按第 5 章笔形/构形规则学习时，容易被表层形态误导、需要直接记忆的字根归并或分流项。",
        "",
    ]
    for group in ROOT_GROUPS:
        lines.extend([
            f"## {group.name}",
            "",
            group.reason,
            "",
            "| 字根 | 组件码 | 字根字码 | 备注 |",
            "| --- | --- | --- | --- |",
        ])
        for root in group.roots:
            if root not in roots:
                lines.append(f"| `{root}` |  |  | 未在 `roots.txt` 中找到 |")
                continue
            code, suffix = roots[root]
            char_code = root_char_code(code, suffix)
            note = "补码为旧资料特殊标记" if suffix == "*" else ""
            lines.append(f"| `{root}` | `{code}` | `{char_code}` | {note} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成郑码字根分布例外清单")
    parser.add_argument("--roots", type=Path, default=DEFAULT_ROOTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roots = read_roots(args.roots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(roots), encoding="utf-8", newline="\n")
    print(f"写出：{args.output}")


if __name__ == "__main__":
    main()
