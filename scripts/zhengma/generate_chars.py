#!/usr/bin/env python3
"""根据字根表和拆分表生成郑码单字码表。

本脚本复现目前已经确认的生成流程：

1. 从 ``data/roots.txt`` 读取字根组件码。
2. 从 ``data/split.txt`` 按 Unicode 顺序读取单字拆分。
3. 根据拆分生成基础全码条目。
4. 在对应字的基础条目之后合入 ``prototypes/*.txt`` 中的单字简码原型。

旧郑码资料仍有少量特殊取位规则。本脚本编码了目前从仓库数据中
提取出的规则，可用 ``--check`` 查看尚未复现的差异。
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_ROOTS = SCRIPT_DIR / "data" / "roots.txt"
DEFAULT_SPLIT = SCRIPT_DIR / "data" / "split.txt"
DEFAULT_CHARS = SCRIPT_DIR / "data" / "chars.txt"
DEFAULT_PROTOTYPES = SCRIPT_DIR / "prototypes"

TOKEN_RE = re.compile(r"\{[^}]+\}|.")


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def tokenize_split(value: str) -> list[str]:
    return TOKEN_RE.findall(value)


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


def read_split(path: Path) -> list[tuple[str, list[str]]]:
    rows: list[tuple[str, list[str]]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        rows.append((parts[1], parts[2:]))
    return rows


def read_prototypes(path: Path) -> tuple[dict[str, str], dict[str, list[tuple[str, str]]]]:
    stem_by_char: dict[str, str] = {}
    rows_by_char: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for name in ("one_code.txt", "two_code.txt", "three_code.txt"):
        proto_path = path / name
        if not proto_path.exists():
            continue
        for raw_line in proto_path.read_text(encoding="utf-8").splitlines():
            if not raw_line or raw_line.startswith("#"):
                continue
            parts = raw_line.split("\t")
            if len(parts) < 2:
                continue
            stem = parts[3] if len(parts) >= 4 else ""
            stem_by_char[parts[0]] = stem
            rows_by_char[parts[0]].append((parts[1], stem))
    return stem_by_char, rows_by_char


def component_code(root: str, roots: dict[str, tuple[str, str]]) -> str:
    return roots[root][0]


def root_char_code(root: str, roots: dict[str, tuple[str, str]]) -> str:
    code, suffix = roots[root]
    return code + suffix


def should_have_stem(char: str) -> bool:
    return ord(char) == 0x3007 or ord(char) >= 0x3400


def pad_short_code(code: str) -> str:
    return code + "vv" if len(code) == 2 else code


def base_code(tokens: list[str], roots: dict[str, tuple[str, str]]) -> str:
    codes = [component_code(token, roots) for token in tokens]
    count = len(codes)
    if count == 1:
        return root_char_code(tokens[0], roots)
    if count == 2:
        return pad_short_code((codes[0] + codes[1])[:4])
    if count == 3:
        return pad_short_code((codes[0] + codes[1][0] + codes[2])[:4])
    if count == 4:
        if len(codes[0]) >= 2:
            return pad_short_code((codes[0] + codes[2][0] + codes[3][0])[:4])
        return pad_short_code((codes[0][0] + codes[1][0] + codes[2][0] + codes[3][0])[:4])
    if len(codes[0]) >= 2:
        return pad_short_code((codes[0] + codes[-2][0] + codes[-1][0])[:4])
    return pad_short_code((codes[0][0] + codes[1][0] + codes[-2][0] + codes[-1][0])[:4])


def default_stem(char: str, tokens: list[str], roots: dict[str, tuple[str, str]]) -> str:
    if not should_have_stem(char):
        return ""
    if len(tokens) == 1:
        code = root_char_code(tokens[0], roots)
        return code[:2] if len(code) >= 2 else code + "v"
    codes = [component_code(token, roots) for token in tokens]
    return (codes[0][0] + codes[1][0])[:2]


def add_unique(rows: list[tuple[str, ...]], seen: set[tuple[str, ...]], row: tuple[str, ...]) -> None:
    if row not in seen:
        seen.add(row)
        rows.append(row)


def generate_rows(
    roots: dict[str, tuple[str, str]],
    split_rows: Iterable[tuple[str, list[str]]],
    prototype_stems: dict[str, str],
    prototypes: dict[str, list[tuple[str, str]]],
) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()

    for char, decompositions in split_rows:
        first_tokens = tokenize_split(decompositions[0])
        stem = prototype_stems.get(char, default_stem(char, first_tokens, roots))

        for decomposition in decompositions:
            tokens = tokenize_split(decomposition)
            code = base_code(tokens, roots)
            row = (char, code, stem) if stem else (char, code)
            add_unique(rows, seen, row)

        for code, proto_stem in prototypes.get(char, []):
            row = (char, code, proto_stem) if proto_stem else (char, code)
            add_unique(rows, seen, row)

    return rows


def format_rows(rows: Iterable[tuple[str, ...]]) -> str:
    return "\n".join("\t".join(row) for row in rows) + "\n"


def read_chars(path: Path) -> list[tuple[str, ...]]:
    return [tuple(line.split("\t")) for line in path.read_text(encoding="utf-8").splitlines()]


def print_check(generated: list[tuple[str, ...]], expected: list[tuple[str, ...]], limit: int) -> bool:
    ok = generated == expected
    print(f"生成行数={len(generated)} 期望行数={len(expected)} 完全一致={'是' if ok else '否'}")
    if ok:
        return True

    for index, (got, want) in enumerate(zip(generated, expected), start=1):
        if got != want:
            print(f"首个差异行={index}")
            print(f"生成：{' '.join(got)}")
            print(f"期望：{' '.join(want)}")
            break

    generated_set = set(generated)
    expected_set = set(expected)
    missing = [row for row in expected if row not in generated_set]
    extra = [row for row in generated if row not in expected_set]
    print(f"缺失行数={len(missing)} 多余行数={len(extra)}")
    for row in missing[:limit]:
        print(f"缺失：{' '.join(row)}")
    for row in extra[:limit]:
        print(f"多余：{' '.join(row)}")
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 scripts/zhengma/data/chars.txt")
    parser.add_argument("--roots", type=Path, default=DEFAULT_ROOTS)
    parser.add_argument("--split", type=Path, default=DEFAULT_SPLIT)
    parser.add_argument("--prototypes", type=Path, default=DEFAULT_PROTOTYPES)
    parser.add_argument("--output", type=Path, help="把生成的单字码表写入此路径")
    parser.add_argument("--check", type=Path, nargs="?", const=DEFAULT_CHARS,
                        help="将生成结果与现有 chars.txt 比较")
    parser.add_argument("--limit", type=int, default=20, help="--check 输出的差异样例上限")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = read_roots(resolve(args.roots))
    split_rows = read_split(resolve(args.split))
    prototype_stems, prototypes = read_prototypes(resolve(args.prototypes))
    rows = generate_rows(roots, split_rows, prototype_stems, prototypes)

    if args.output:
        resolve(args.output).write_text(format_rows(rows), encoding="utf-8", newline="\n")

    if args.check:
        expected = read_chars(resolve(args.check))
        return 0 if print_check(rows, expected, args.limit) else 1

    if not args.output:
        print(format_rows(rows), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
