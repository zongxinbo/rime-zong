#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "schemas" / "common" / "words"


def parse_rime_dict(path: Path) -> tuple[list[str], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header: list[str] = []
    body: list[str] = []
    in_body = False

    for line in lines:
        if line.strip() == "...":
            in_body = True
            continue
        if in_body:
            if line and not line.startswith("#"):
                body.append(line)
        else:
            header.append(line)

    if not in_body:
        raise ValueError(f"{path} 不是有效的 Rime dict yaml：缺少 ... 分隔行")
    return header, body


def extract_text_entries(body: list[str], source: Path) -> list[str]:
    entries: list[str] = []
    seen: set[str] = set()
    for lineno, line in enumerate(body, start=1):
        text = line.split("\t", 1)[0].strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        entries.append(text)
    if not entries:
        raise ValueError(f"{source} 未解析到词条")
    return entries


def write_words_dict(source: Path, output: Path, *, name: str) -> int:
    _, body = parse_rime_dict(source)
    entries = extract_text_entries(body, source)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# encoding: utf-8",
        "---",
        f'name: "{name}"',
        'version: "20260302"',
        "sort: original",
        "columns:",
        "  - text",
        "...",
        "",
        *entries,
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return len(entries)


def main() -> None:
    parser = argparse.ArgumentParser(description="转换宇浩星陈词库为通用纯文本 Rime 词库")
    parser.add_argument("--sc-source", required=True, type=Path, help="简体 yustar_sc.words.dict.yaml 源文件")
    parser.add_argument("--tc-source", required=True, type=Path, help="繁体 yustar_tc.words.dict.yaml 源文件")
    parser.add_argument("--mixed-source", type=Path, help="简繁混合 yustar.words.dict.yaml 源文件")
    parser.add_argument(
        "--mixed-output",
        type=Path,
        help="简繁混合词库输出路径；仅在提供 --mixed-source 时使用",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"输出目录，默认 {DEFAULT_OUTPUT_DIR}",
    )
    args = parser.parse_args()

    sc_count = write_words_dict(
        args.sc_source,
        args.output_dir / "sc.words.dict.yaml",
        name="sc.words",
    )
    tc_count = write_words_dict(
        args.tc_source,
        args.output_dir / "tc.words.dict.yaml",
        name="tc.words",
    )
    mixed_count = None
    mixed_output = args.mixed_output
    if args.mixed_source is not None:
        if mixed_output is None:
            mixed_output = args.output_dir / "mixed.words.dict.yaml"
        mixed_count = write_words_dict(
            args.mixed_source,
            mixed_output,
            name=mixed_output.name.removesuffix(".dict.yaml"),
        )
    print(f"生成 {args.output_dir / 'sc.words.dict.yaml'}：{sc_count} 条")
    print(f"生成 {args.output_dir / 'tc.words.dict.yaml'}：{tc_count} 条")
    if mixed_count is not None and mixed_output is not None:
        print(f"生成 {mixed_output}：{mixed_count} 条")


if __name__ == "__main__":
    main()
