#!/usr/bin/env python3
from __future__ import annotations

import argparse

from core.builder import build_chars_prototype


def main() -> None:
    parser = argparse.ArgumentParser(description="生成双拼单字原型表，并挂接仓颉首尾辅助码。")
    parser.add_argument(
        "--simplified",
        dest="simplified",
        action="store_true",
        default=True,
        help="使用简体字频列生成单字主读音和排序权重（默认）。",
    )
    parser.add_argument(
        "--traditional",
        dest="simplified",
        action="store_false",
        help="使用繁体字频列生成单字主读音和排序权重。",
    )
    parser.add_argument("--schema", choices=["zrm", "flypy"], default="zrm", help="目标双拼方案。")
    args = parser.parse_args()

    entries, dropped, path = build_chars_prototype(args.schema, simplified=args.simplified)
    print(f"已生成 {path}")
    print(f"单字原型条目数：{len(entries)}")
    print(f"因缺少可用仓颉辅助码而丢弃的字符数：{len(dropped)}")


if __name__ == "__main__":
    main()
