#!/usr/bin/env python3
"""按 schema_id 拷贝 Rime 方案依赖到输出目录。"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from scheme_dependencies import DependencyScanner, REPO_ROOT, rel


DEFAULT_OUTPUT = REPO_ROOT / "_output"


def deploy_path(source: Path) -> Path:
    """转换为 Rime 用户目录中的目标相对路径。"""
    relative = source.resolve().relative_to(REPO_ROOT)
    if relative.parts and relative.parts[0] in {"lua", "opencc"}:
        return Path(*relative.parts)
    return Path(source.name)


def ensure_safe_clean(output: Path) -> None:
    resolved = output.resolve()
    root = REPO_ROOT.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"清理目录必须位于仓库内：{resolved}")
    if not resolved.name.startswith("_"):
        raise ValueError(f"清理目录名必须以 _ 开头：{resolved}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="根据一个或多个 schema_id 拷贝所需文件到输出目录。"
    )
    parser.add_argument(
        "schema_ids",
        nargs="+",
        help="要拷贝的方案 ID，可用空格分开传入多个，例如 sancang5 cangjie5",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="输出目录，默认 _output",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="拷贝前清空输出目录；为安全起见，目录必须位于仓库内且名称以 _ 开头",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    if args.clean and output.exists():
        ensure_safe_clean(output)
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    scanner = DependencyScanner()
    copied: dict[Path, Path] = {}
    missing: set[str] = set()
    external_presets: set[str] = set()
    external_vocabularies: set[str] = set()

    for schema_id in args.schema_ids:
        closure = scanner.collect(schema_id)
        if not closure.schema_files:
            print(f"找不到方案：{schema_id}", file=sys.stderr)
            return 2
        missing.update(closure.missing)
        external_presets.update(closure.external_presets)
        external_vocabularies.update(closure.external_vocabularies)

        for source in closure.files:
            target_relative = deploy_path(source)
            previous = copied.get(target_relative)
            if previous and previous.resolve() != source.resolve():
                print(
                    f"目标文件冲突：{target_relative} 来自 {rel(previous)} 和 {rel(source)}",
                    file=sys.stderr,
                )
                return 3
            copied[target_relative] = source

    for target_relative, source in sorted(copied.items(), key=lambda item: item[0].as_posix()):
        target = output / target_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        print(f"{rel(source)} -> {target.relative_to(output).as_posix()}")

    print(f"完成：方案={', '.join(args.schema_ids)} 文件={len(copied)} 输出={output}", file=sys.stderr)
    if external_presets:
        print(f"外部预设：{', '.join(sorted(external_presets))}", file=sys.stderr)
    if external_vocabularies:
        print(f"外部词语模型：{', '.join(sorted(external_vocabularies))}", file=sys.stderr)
    if missing:
        print(f"缺失资源：{', '.join(sorted(missing))}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
