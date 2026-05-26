from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from collections import Counter, defaultdict

from scripts.cangjie.core.cangjie_builder import (
    get_weighted_frequencies,
    is_han_char,
    parse_cangjie_dict,
)

from .mapping import EncodedChar, encode_lingcang
from .paths import ONE_CODE_PATH, OUTPUT_DICT, REPORT_PATH, SOURCE_DICT, TWO_CODE_PATH


def load_shortcuts(scores: dict[str, int]) -> list[EncodedChar]:
    entries: list[EncodedChar] = []
    for path, source_prefix in [(ONE_CODE_PATH, "S1"), (TWO_CODE_PATH, "S2")]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            text, code = parts[0], parts[1]
            entries.append(
                EncodedChar(
                    text=text,
                    source_code=f"{source_prefix}:{code}",
                    code=code,
                    weight=scores.get(text, 0),
                )
            )
    return entries


def build_entries(*, only_first_full_code: bool = False) -> list[EncodedChar]:
    scores = get_weighted_frequencies()
    raw_entries = parse_cangjie_dict(SOURCE_DICT)

    shortcut_entries = load_shortcuts(scores)
    seen_chars: set[str] = set()
    seen_text_code: set[tuple[str, str]] = {(entry.text, entry.code) for entry in shortcut_entries}
    entries: list[EncodedChar] = []
    skipped_prefix_code = 0
    skipped_unknown_code = 0
    for entry in raw_entries:
        if not is_han_char(entry.text):
            continue
        if entry.code.startswith(("z", "x")):
            skipped_prefix_code += 1
            continue
        if only_first_full_code and entry.text in seen_chars:
            continue
        seen_chars.add(entry.text)

        try:
            code = encode_lingcang(entry.code)
        except KeyError:
            skipped_unknown_code += 1
            continue
        item = (entry.text, code)
        if item in seen_text_code:
            continue
        seen_text_code.add(item)
        entries.append(
            EncodedChar(
                text=entry.text,
                source_code=entry.code,
                code=code,
                weight=scores.get(entry.text, 0),
            )
        )

    entries.sort(key=lambda item: (item.code, -item.weight, item.source_code, item.text))
    build_entries.skipped_prefix_code = skipped_prefix_code
    build_entries.skipped_unknown_code = skipped_unknown_code
    build_entries.shortcut_count = len(shortcut_entries)
    build_entries.full_count = len(entries)
    return shortcut_entries + entries


def render_dict(entries: list[EncodedChar]) -> str:
    header = [
        "# encoding: utf-8",
        "# 由 scripts/lingcang/gen_lingcang.py 生成",
        "---",
        "name: lingcang",
        f"version: '{dt.date.today().isoformat()}'",
        "sort: by_weight",
        "...",
        "",
    ]
    body = [f"{entry.text}\t{entry.code}" for entry in entries]
    return "\n".join(header + body) + "\n"


def write_dict(entries: list[EncodedChar]) -> None:
    OUTPUT_DICT.parent.mkdir(parents=True, exist_ok=True)
    temp_output = OUTPUT_DICT.with_name(OUTPUT_DICT.name + ".tmp")
    temp_output.write_text(render_dict(entries), encoding="utf-8", newline="\n")
    temp_output.replace(OUTPUT_DICT)


def _run_summary() -> str:
    command = [
        sys.executable,
        "scripts/assess/summary.py",
        "--dict",
        str(OUTPUT_DICT),
        "--commit-suffixes",
        "aeiou",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
    return result.stdout


def _split_table(line: str) -> list[str]:
    return [cell.strip() for cell in line.split("|")]


def _markdown_table(lines: list[str]) -> list[str]:
    table_lines = [line for line in lines if "|" in line and not set(line.strip()) <= {"-"}]
    if not table_lines:
        return []
    rows = [_split_table(line) for line in table_lines]
    col_count = max(len(row) for row in rows)
    rows = [row + [""] * (col_count - len(row)) for row in rows]

    out = ["| " + " | ".join(rows[0]) + " |"]
    out.append("| :--- | " + " | ".join("---:" for _ in range(col_count - 1)) + " |")
    for row in rows[1:]:
        out.append("| " + " | ".join(row) + " |")
    return out


def _summary_sections(summary: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    section_re = re.compile(r"=+\s+\[(\d+)\]\s+(.+?)\s+=+")
    for line in summary.splitlines():
        match = section_re.match(line)
        if match:
            current = match.group(1)
            sections[current] = []
            continue
        if current:
            sections[current].append(line.rstrip())
    return sections


def _parse_percent(line: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)%", line)
    return float(match.group(1)) if match else None


def _render_summary_markdown(summary: str) -> list[str]:
    sections = _summary_sections(summary)
    lines = [
        "## 测评摘要",
        "",
        "评估命令：",
        "",
        "```powershell",
        "python scripts\\assess\\summary.py --dict schemas\\lingcang\\lingcang.dict.yaml --commit-suffixes aeiou",
        "```",
        "",
    ]

    headings = {
        "1": "静态重码",
        "2": "动态选重率",
        "3": "候选数",
        "4": "速度当量",
        "5": "加权平均码长",
    }
    for key, heading in headings.items():
        lines.extend([f"### {heading}", ""])
        lines.extend(_markdown_table(sections.get(key, [])))
        lines.append("")

    heatmap = sections.get("6", [])
    hand_load: dict[str, float] = {}
    finger_load: dict[str, float] = {}
    row_load: dict[str, float] = {}
    current_bucket: str | None = None
    for raw_line in heatmap:
        line = raw_line.strip()
        if line.startswith("[左右手平衡"):
            current_bucket = "hand"
            continue
        if line.startswith("[手指负载"):
            current_bucket = "finger"
            continue
        if line.startswith("[排级负载"):
            current_bucket = "row"
            continue
        if ":" not in line:
            continue
        name = line.split(":", 1)[0].strip()
        value = _parse_percent(line)
        if value is None:
            continue
        if current_bucket == "hand":
            hand_load[name] = value
        elif current_bucket == "finger":
            finger_load[name] = value
        elif current_bucket == "row":
            row_load[name] = value

    if hand_load or finger_load or row_load:
        lines.extend(["### 键位负载摘要", ""])
        if hand_load:
            left = hand_load.get("左手", 0.0)
            right = hand_load.get("右手", 0.0)
            lines.append(f"- 左右手：左手 {left:.1f}%，右手 {right:.1f}%。")
        if finger_load:
            top_finger, top_value = max(finger_load.items(), key=lambda item: item[1])
            second_finger, second_value = sorted(finger_load.items(), key=lambda item: item[1], reverse=True)[1]
            lines.append(f"- 手指最高负载：{top_finger} {top_value:.1f}%，{second_finger} {second_value:.1f}%。")
        if row_load:
            row_order = ["上排", "中排", "下排", "空格排", "数字排"]
            row_text = "，".join(f"{name} {row_load.get(name, 0.0):.1f}%" for name in row_order)
            lines.append(f"- 排级负载：{row_text}。")
        lines.append("")

    return lines


def write_report(entries: list[EncodedChar]) -> None:
    code_groups: dict[str, list[EncodedChar]] = defaultdict(list)
    for entry in entries:
        code_groups[entry.code].append(entry)

    collision_groups = [group for group in code_groups.values() if len(group) > 1]
    max_group = max((len(group) for group in code_groups.values()), default=0)
    length_counts = Counter(len(entry.code) for entry in entries)
    lines = [
        "# 灵仓生成报告",
        "",
        "## 生成统计",
        "",
        f"- 总条目：{len(entries)}",
        f"- 简码条目：{getattr(build_entries, 'shortcut_count', 0)}",
        f"- 全码条目：{getattr(build_entries, 'full_count', len(entries))}",
        f"- 唯一码位：{len(code_groups)}",
        f"- 重码组：{len(collision_groups)}",
        f"- 最大候选数：{max_group}",
        f"- 跳过 x/z 前缀编码：{getattr(build_entries, 'skipped_prefix_code', 0)}",
        f"- 跳过内部未知根编码：{getattr(build_entries, 'skipped_unknown_code', 0)}",
        "- 码长分布："
    ]
    for length in sorted(length_counts):
        lines.append(f"  - {length} 码：{length_counts[length]}")
    lines.append("")
    lines.extend(_render_summary_markdown(_run_summary()))
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def generate_lingcang(*, only_first_full_code: bool = False) -> list[EncodedChar]:
    entries = build_entries(only_first_full_code=only_first_full_code)
    write_dict(entries)
    write_report(entries)
    return entries
