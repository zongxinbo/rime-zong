#!/usr/bin/env python3
"""从类词典来源提取郑码简码原型。"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_SOURCE_DICT = REPO_ROOT / "schemas" / "zhengma" / "zmsj" / "zmsj.dict.yaml"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "prototypes"
README_PATH = SCRIPT_DIR / "README.md"


@dataclass(frozen=True)
class DictEntry:
    text: str
    code: str
    weight: str = ""
    stem: str = ""


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def looks_like_code(value: str) -> bool:
    return bool(value) and value.isascii() and value.isalpha() and value.islower()


HAN_RANGES = (
    (0x3400, 0x4DBF),      # 中日韩扩展 A
    (0x4E00, 0x9FFF),      # 中日韩统一表意文字
    (0xF900, 0xFAFF),      # 中日韩兼容表意文字
    (0x20000, 0x2A6DF),    # 中日韩扩展 B
    (0x2A700, 0x2B73F),    # 中日韩扩展 C
    (0x2B740, 0x2B81F),    # 中日韩扩展 D
    (0x2B820, 0x2CEAF),    # 中日韩扩展 E
    (0x2CEB0, 0x2EBEF),    # 中日韩扩展 F
    (0x30000, 0x3134F),    # 中日韩扩展 G
    (0x31350, 0x323AF),    # 中日韩扩展 H
    (0x2EBF0, 0x2EE5F),    # 中日韩扩展 I
)


def is_han_char(char: str) -> bool:
    codepoint = ord(char)
    return any(start <= codepoint <= end for start, end in HAN_RANGES)


def is_han_text(text: str) -> bool:
    return bool(text) and all(is_han_char(char) for char in text)


def parse_row(parts: list[str], source_format: str) -> DictEntry | None:
    if len(parts) < 2:
        return None
    if source_format == "code-text":
        code, text = parts[0], parts[1]
        weight = parts[2] if len(parts) >= 3 else ""
        stem = parts[3] if len(parts) >= 4 else ""
    else:
        text, code = parts[0], parts[1]
        weight = parts[2] if len(parts) >= 3 else ""
        stem = parts[3] if len(parts) >= 4 else ""
    return DictEntry(text=text, code=code, weight=weight, stem=stem)


def iter_dict_entries(path: Path, *, source_format: str) -> list[DictEntry]:
    entries: list[DictEntry] = []
    in_body = False
    has_header = False
    effective_format = source_format
    encoding = "utf-8"
    with path.open("rb") as f:
        prefix = f.read(4)
    if prefix.startswith(b"\xff\xfe") or prefix.startswith(b"\xfe\xff"):
        encoding = "utf-16"
    elif prefix.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"

    with path.open("r", encoding=encoding) as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            if line.strip() == "...":
                in_body = True
                has_header = True
                if effective_format == "auto":
                    effective_format = "text-code"
                continue
            if not in_body and line.strip() == "---":
                has_header = True
                continue
            if has_header and not in_body:
                continue

            parts = line.split("\t")
            if effective_format == "auto":
                effective_format = "code-text" if looks_like_code(parts[0]) else "text-code"
            entry = parse_row(parts, effective_format)
            if entry is not None:
                entries.append(entry)

    return entries


def rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def output_label(output_dir: Path) -> str:
    try:
        return output_dir.relative_to(SCRIPT_DIR).as_posix()
    except ValueError:
        return rel(output_dir)


def write_entries(path: Path, entries: list[DictEntry], *, title: str, source_dict: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"# {title}\n")
        f.write(f"# 来源：{rel(source_dict)}\n")
        f.write("# 列：词条\t编码\t权重\t造词码\n")
        for entry in entries:
            f.write(f"{entry.text}\t{entry.code}\t{entry.weight}\t{entry.stem}\n")


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip() and not line.startswith("#"))


def collect_existing_summaries() -> list[tuple[str, dict[str, int]]]:
    summaries: list[tuple[str, dict[str, int]]] = []
    for output_dir in sorted(SCRIPT_DIR.glob("prototypes_*")):
        if not output_dir.is_dir():
            continue
        summaries.append((
            output_label(output_dir),
            {
                "one_code": count_rows(output_dir / "one_code.txt"),
                "two_code": count_rows(output_dir / "two_code.txt"),
                "three_code": count_rows(output_dir / "three_code.txt"),
                "phrase_shortcuts": count_rows(output_dir / "phrase_shortcuts.txt"),
            },
        ))
    return summaries


def write_readme() -> None:
    lines = [
        "# 郑码脚本",
        "",
        "本目录保存郑码相关源数据和从各郑码方案提取出的简码原型。",
        "",
        "## 数据",
        "",
        "- `data/chars.txt`：单字码表",
        "- `data/roots.txt`：字根表",
        "- `data/split.txt`：拆分表",
        "- `data/README.md`：原始数据说明",
        "",
        "## 简码原型",
        "",
        "原型由 `extract_prototypes.py` 提取。脚本按同一词条的全部编码分组，短于该词条最长编码的入口才视为简码。",
        "",
        "| 目录 | 一简 | 二简 | 三简 | 简码词 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label, counts in collect_existing_summaries():
        lines.append(
            f"| `{label}` | {counts['one_code']} | {counts['two_code']} | "
            f"{counts['three_code']} | {counts['phrase_shortcuts']} |"
        )
    lines.extend([
        "",
        "重新生成示例：",
        "",
        "```powershell",
        "python scripts/zhengma/extract_prototypes.py --source-dict schemas/zhengma/zmsj/zmsj.dict.yaml --output-dir scripts/zhengma/prototypes_zmsj",
        "```",
        "",
    ])
    README_PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="提取郑码简码原型")
    parser.add_argument("--source-dict", type=Path, default=DEFAULT_SOURCE_DICT,
                        help="源词典文件；支持 Rime text-code 格式或无 header 的 code-text 格式")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="输出目录，默认 scripts/zhengma/prototypes")
    parser.add_argument("--source-format", choices=("auto", "text-code", "code-text"), default="auto",
                        help="字段顺序；auto 对 Rime dict 使用 text-code，对无 header 文件按首列是否像编码识别")
    parser.add_argument("--no-readme", action="store_true", help="不更新 scripts/zhengma/README.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dict = resolve_path(args.source_dict)
    output_dir = resolve_path(args.output_dir)

    entries = [
        entry for entry in iter_dict_entries(source_dict, source_format=args.source_format)
        if is_han_text(entry.text)
    ]
    max_code_lengths: dict[str, int] = {}
    for entry in entries:
        max_code_lengths[entry.text] = max(max_code_lengths.get(entry.text, 0), len(entry.code))

    one_code_by_code: dict[str, DictEntry] = {}
    for entry in entries:
        if len(entry.text) == 1 and len(entry.code) == 1 and entry.code not in one_code_by_code:
            one_code_by_code[entry.code] = entry
    one_code = [
        one_code_by_code[code]
        for code in sorted(one_code_by_code)
    ]

    shortcut_entries = [
        entry for entry in entries
        if len(entry.code) < max_code_lengths[entry.text]
    ]
    two_code = [entry for entry in shortcut_entries if len(entry.text) == 1 and len(entry.code) == 2]
    three_code = [entry for entry in shortcut_entries if len(entry.text) == 1 and len(entry.code) == 3]
    phrase_shortcuts = [
        entry for entry in shortcut_entries
        if len(entry.text) > 1
    ]

    write_entries(output_dir / "one_code.txt", one_code, title="一简单字", source_dict=source_dict)
    write_entries(output_dir / "two_code.txt", two_code, title="二简单字", source_dict=source_dict)
    write_entries(output_dir / "three_code.txt", three_code, title="三简单字", source_dict=source_dict)
    write_entries(output_dir / "phrase_shortcuts.txt", phrase_shortcuts, title="简码词", source_dict=source_dict)
    if not args.no_readme:
        write_readme()

    print(f"一简={len(one_code)}")
    print(f"二简={len(two_code)}")
    print(f"三简={len(three_code)}")
    print(f"简码词={len(phrase_shortcuts)}")
    print(f"输出目录={rel(output_dir)}")


if __name__ == "__main__":
    main()
